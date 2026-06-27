#!/usr/bin/env python3
"""
knowledge_vault.py — Second brain for trading knowledge.

SQLite-backed store with FTS5 full-text search and markdown export.
Organizes insights into 5 categories: concepts, patterns, rules, risk, psychology.

Usage:
    python knowledge_vault.py --stats [--vault-dir PATH]
    python knowledge_vault.py --search "order block" [--category patterns]
    python knowledge_vault.py --add-insight --category patterns --title "FVG Entry" --content "..."
    python knowledge_vault.py --list-sources
    python knowledge_vault.py --export-insights [--vault-dir PATH]
    python knowledge_vault.py --sample
"""

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

VAULT_DIR_DEFAULT = Path.home() / ".trading-vault"
CATEGORIES = ["concepts", "patterns", "rules", "risk", "psychology"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    source_type TEXT NOT NULL,  -- youtube | discord | platform | manual
    source_id TEXT,
    title TEXT,
    url TEXT,
    channel TEXT,
    ingested_at TEXT,
    file_path TEXT
);

CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    category TEXT NOT NULL,  -- concepts | patterns | rules | risk | psychology
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT,  -- comma-separated
    confidence_raw REAL DEFAULT 1.0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS insights_fts
    USING fts5(title, content, tags, content='insights', content_rowid='id');

CREATE TRIGGER IF NOT EXISTS insights_ai AFTER INSERT ON insights BEGIN
    INSERT INTO insights_fts(rowid, title, content, tags)
    VALUES (new.id, new.title, new.content, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS insights_ad AFTER DELETE ON insights BEGIN
    INSERT INTO insights_fts(insights_fts, rowid, title, content, tags)
    VALUES ('delete', old.id, old.title, old.content, old.tags);
END;

CREATE TABLE IF NOT EXISTS pattern_occurrences (
    id INTEGER PRIMARY KEY,
    pattern_key TEXT NOT NULL,  -- normalized pattern identifier
    insight_id INTEGER REFERENCES insights(id),
    source_id INTEGER REFERENCES sources(id),
    occurred_at TEXT DEFAULT (datetime('now'))
);
"""


def _get_db(vault_dir: Path) -> sqlite3.Connection:
    vault_dir.mkdir(parents=True, exist_ok=True)
    db_path = vault_dir / "vault.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def register_source(vault_dir: Path, source_type: str, source_id: str,
                    title: str, url: str = "", channel: str = "",
                    file_path: str = "") -> int:
    """Register an ingested source; return its DB id."""
    conn = _get_db(vault_dir)
    cur = conn.execute(
        "INSERT INTO sources (source_type, source_id, title, url, channel, ingested_at, file_path) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (source_type, source_id, title, url, channel,
         datetime.utcnow().isoformat(), file_path),
    )
    conn.commit()
    return cur.lastrowid


def add_insight(vault_dir: Path, category: str, title: str, content: str,
                source_id: Optional[int] = None, tags: str = "") -> int:
    if category not in CATEGORIES:
        raise ValueError(f"Category must be one of: {', '.join(CATEGORIES)}")
    conn = _get_db(vault_dir)
    cur = conn.execute(
        "INSERT INTO insights (source_id, category, title, content, tags) VALUES (?, ?, ?, ?, ?)",
        (source_id, category, title, content, tags),
    )
    conn.commit()
    return cur.lastrowid


def search_insights(vault_dir: Path, query: str, category: Optional[str] = None,
                    limit: int = 20) -> list:
    conn = _get_db(vault_dir)
    if category:
        rows = conn.execute(
            "SELECT i.id, i.category, i.title, i.content, i.tags, i.created_at, "
            "s.source_type, s.title as source_title, s.url "
            "FROM insights_fts f "
            "JOIN insights i ON f.rowid = i.id "
            "LEFT JOIN sources s ON i.source_id = s.id "
            "WHERE insights_fts MATCH ? AND i.category = ? LIMIT ?",
            (query, category, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT i.id, i.category, i.title, i.content, i.tags, i.created_at, "
            "s.source_type, s.title as source_title, s.url "
            "FROM insights_fts f "
            "JOIN insights i ON f.rowid = i.id "
            "LEFT JOIN sources s ON i.source_id = s.id "
            "WHERE insights_fts MATCH ? LIMIT ?",
            (query, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_stats(vault_dir: Path) -> dict:
    conn = _get_db(vault_dir)
    total_sources = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    sources_by_type = dict(conn.execute(
        "SELECT source_type, COUNT(*) FROM sources GROUP BY source_type"
    ).fetchall())
    total_insights = conn.execute("SELECT COUNT(*) FROM insights").fetchone()[0]
    by_category = dict(conn.execute(
        "SELECT category, COUNT(*) FROM insights GROUP BY category"
    ).fetchall())
    recent = conn.execute(
        "SELECT source_type, title, ingested_at FROM sources ORDER BY ingested_at DESC LIMIT 5"
    ).fetchall()
    return {
        "total_sources": total_sources,
        "sources_by_type": sources_by_type,
        "total_insights": total_insights,
        "insights_by_category": by_category,
        "recent_ingests": [dict(r) for r in recent],
        "vault_dir": str(vault_dir),
        "db_size_kb": round((vault_dir / "vault.db").stat().st_size / 1024, 1)
        if (vault_dir / "vault.db").exists() else 0,
    }


def export_insights_to_markdown(vault_dir: Path):
    """Write categorized insight files to vault/insights/."""
    conn = _get_db(vault_dir)
    insights_dir = vault_dir / "insights"
    insights_dir.mkdir(exist_ok=True)

    for cat in CATEGORIES:
        rows = conn.execute(
            "SELECT i.title, i.content, i.tags, i.created_at, s.source_type, s.title as src, s.url "
            "FROM insights i LEFT JOIN sources s ON i.source_id = s.id "
            "WHERE i.category = ? ORDER BY i.created_at",
            (cat,),
        ).fetchall()

        lines = [f"# {cat.title()} Insights", "",
                 f"_Last exported: {datetime.utcnow().isoformat()[:16]}Z_", "",
                 f"**{len(rows)} insights in this category**", ""]

        for r in rows:
            lines += [
                f"## {r['title']}",
                "",
                r["content"],
                "",
                f"_Source: {r['source_type'] or 'manual'} — {r['src'] or 'manual entry'}_",
                "",
                "---",
                "",
            ]

        (insights_dir / f"{cat}.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"  Exported {len(rows)} {cat} insights")


def list_sources(vault_dir: Path) -> list:
    conn = _get_db(vault_dir)
    rows = conn.execute(
        "SELECT source_type, title, channel, ingested_at, url FROM sources ORDER BY ingested_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def main():
    parser = argparse.ArgumentParser(description="Trading Knowledge Vault — second brain CLI.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--stats", action="store_true")
    group.add_argument("--search", metavar="QUERY")
    group.add_argument("--add-insight", action="store_true")
    group.add_argument("--list-sources", action="store_true")
    group.add_argument("--export-insights", action="store_true")
    group.add_argument("--sample", action="store_true")

    parser.add_argument("--vault-dir", default=str(VAULT_DIR_DEFAULT))
    parser.add_argument("--category", choices=CATEGORIES)
    parser.add_argument("--title")
    parser.add_argument("--content")
    parser.add_argument("--tags", default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.sample:
        print(json.dumps({"total_sources": 23, "sources_by_type": {"youtube": 15, "discord": 5, "platform": 3},
                          "total_insights": 187, "insights_by_category": {"concepts": 42, "patterns": 61,
                          "rules": 38, "risk": 29, "psychology": 17}}, indent=2))
        return

    vault_dir = Path(args.vault_dir)

    if args.stats:
        stats = get_stats(vault_dir)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"\n=== Trading Knowledge Vault ===")
            print(f"  Location: {vault_dir}")
            print(f"  DB size: {stats['db_size_kb']} KB")
            print(f"  Sources: {stats['total_sources']} total")
            for t, n in stats["sources_by_type"].items():
                print(f"    {t}: {n}")
            print(f"  Insights: {stats['total_insights']} total")
            for cat, n in stats["insights_by_category"].items():
                print(f"    {cat}: {n}")
            if stats["recent_ingests"]:
                print(f"  Recent:")
                for r in stats["recent_ingests"]:
                    print(f"    [{r['source_type']}] {r['title'][:50]} ({r['ingested_at'][:10]})")

    elif args.search:
        results = search_insights(vault_dir, args.search, category=args.category, limit=args.limit)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\nSearch: '{args.search}' — {len(results)} results")
            for r in results:
                print(f"  [{r['category'].upper()}] {r['title']}")
                print(f"    {r['content'][:120]}...")
                if r.get("url"):
                    print(f"    Source: {r['url'][:60]}")
                print()

    elif args.add_insight:
        if not all([args.category, args.title, args.content]):
            print("Need --category, --title, --content", file=sys.stderr)
            sys.exit(1)
        insight_id = add_insight(vault_dir, args.category, args.title, args.content, tags=args.tags)
        print(f"✓ Added insight #{insight_id}: {args.title} [{args.category}]")

    elif args.list_sources:
        sources = list_sources(vault_dir)
        if args.json:
            print(json.dumps(sources, indent=2))
        else:
            print(f"\n{len(sources)} sources ingested:")
            for s in sources:
                print(f"  [{s['source_type']:8}] {s['title'][:50]} ({s['ingested_at'][:10]})")

    elif args.export_insights:
        export_insights_to_markdown(vault_dir)
        print(f"✓ Insights exported to {vault_dir}/insights/")


if __name__ == "__main__":
    main()
