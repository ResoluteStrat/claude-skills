#!/usr/bin/env python3
"""
strategy_synthesizer.py — Synthesize a trading strategy from the knowledge vault.

Identifies recurring concepts across sources, scores confidence by source count
and diversity, and generates a structured strategy document.

Confidence levels:
  LOW       1 source    — Note, do not trade on
  MODERATE  2-3 sources — Paper trade to validate
  HIGH      4-6 sources — Strong signal, backtest before live
  VERY HIGH 7+ sources  — Core principle, foundational rule

Usage:
    python strategy_synthesizer.py --synthesize [--vault-dir PATH] [--output FILE]
    python strategy_synthesizer.py --confidence-report [--vault-dir PATH]
    python strategy_synthesizer.py --sample
"""

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

VAULT_DIR_DEFAULT = Path.home() / ".trading-vault"

# Keywords that signal importance in trading content
CORE_CONCEPTS = [
    "order block", "orderblock", "ob",
    "fair value gap", "fvg", "imbalance",
    "liquidity", "sweep", "stop hunt",
    "market structure", "structure break", "bos", "choch",
    "support", "resistance",
    "trend", "momentum",
    "volume", "volume profile",
    "kill zone", "session", "london", "new york",
    "fibonacci", "fib", "retracement",
    "risk reward", "r:r", "risk management",
    "stop loss", "take profit",
    "entry", "entry criteria",
    "confluence", "confirmation",
    "higher timeframe", "htf", "ltf",
    "wyckoff", "accumulation", "distribution",
    "ict", "smc", "smart money",
    "price action", "candle", "wick",
    "breakout", "breakout strategy",
    "divergence", "rsi", "macd",
    "moving average", "ema", "sma",
    "consolidation", "range",
    "journal", "trade journal", "review",
    "psychology", "discipline", "patience",
    "backtesting", "forward test",
]


def _confidence_label(n_sources: int) -> str:
    if n_sources >= 7:
        return "VERY HIGH"
    if n_sources >= 4:
        return "HIGH"
    if n_sources >= 2:
        return "MODERATE"
    return "LOW"


def _get_db(vault_dir: Path) -> sqlite3.Connection:
    db_path = vault_dir / "vault.db"
    if not db_path.exists():
        print(f"No vault found at {vault_dir}. Run an ingestor first.", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _extract_concepts_from_text(text: str) -> list:
    """Find which core concepts appear in a block of text."""
    text_lower = text.lower()
    found = []
    for concept in CORE_CONCEPTS:
        if concept in text_lower:
            found.append(concept)
    return found


def _normalize_concept(concept: str) -> str:
    """Normalize concept aliases to canonical form."""
    aliases = {
        "ob": "order block",
        "orderblock": "order block",
        "fvg": "fair value gap",
        "bos": "structure break",
        "choch": "structure break",
        "htf": "higher timeframe",
        "ltf": "lower timeframe",
        "r:r": "risk reward",
        "smc": "smart money",
        "ema": "moving average",
        "sma": "moving average",
    }
    return aliases.get(concept, concept)


def _scan_vault_sources(vault_dir: Path) -> dict:
    """Scan all source files and count concept occurrences per source."""
    concept_sources = defaultdict(set)  # concept -> set of source_ids

    conn = _get_db(vault_dir)
    sources = conn.execute(
        "SELECT id, source_type, title, file_path FROM sources"
    ).fetchall()

    for source in sources:
        file_path = source["file_path"]
        source_id = str(source["id"])

        # Read source file if it exists
        text = ""
        if file_path and Path(file_path).exists():
            try:
                text = Path(file_path).read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass

        # Also scan insights linked to this source
        insights = conn.execute(
            "SELECT title, content FROM insights WHERE source_id = ?",
            (source["id"],)
        ).fetchall()
        for insight in insights:
            text += f" {insight['title']} {insight['content']}"

        for concept in _extract_concepts_from_text(text):
            normalized = _normalize_concept(concept)
            concept_sources[normalized].add(source_id)

    return dict(concept_sources)


def _get_insights_for_concept(vault_dir: Path, concept: str) -> list:
    """Get all insights mentioning this concept."""
    conn = _get_db(vault_dir)
    # FTS search
    try:
        rows = conn.execute(
            "SELECT i.category, i.title, i.content, s.source_type, s.title as src_title "
            "FROM insights_fts f JOIN insights i ON f.rowid = i.id "
            "LEFT JOIN sources s ON i.source_id = s.id "
            "WHERE insights_fts MATCH ? LIMIT 5",
            (concept,),
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []


def _build_strategy_document(vault_dir: Path, concept_sources: dict,
                              instrument: str = "", timeframe: str = "") -> str:
    conn = _get_db(vault_dir)
    total_sources = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    total_insights = conn.execute("SELECT COUNT(*) FROM insights").fetchone()[0]

    now = datetime.utcnow().isoformat()[:10]
    
    # Sort concepts by source count (descending)
    sorted_concepts = sorted(
        concept_sources.items(), key=lambda x: len(x[1]), reverse=True
    )

    lines = [
        "# Trading Strategy — Synthesized from Knowledge Vault",
        "",
        f"**Generated:** {now}  ",
        f"**Sources Analyzed:** {total_sources}  ",
        f"**Insights Analyzed:** {total_insights}  ",
    ]
    if instrument:
        lines.append(f"**Instrument:** {instrument}  ")
    if timeframe:
        lines.append(f"**Timeframe:** {timeframe}  ")

    lines += [
        "",
        "---",
        "",
        "> **Disclaimer:** This strategy is synthesized from educational content you have ingested.",
        "> It represents recurring themes in those sources — not financial advice.",
        "> All rules require personal validation through backtesting and paper trading.",
        "",
        "## Confidence Legend",
        "",
        "| Level | Sources | Action |",
        "|-------|---------|--------|",
        "| `VERY HIGH` | 7+ | Core principle — validate and use |",
        "| `HIGH` | 4-6 | Strong signal — backtest before live |",
        "| `MODERATE` | 2-3 | Recurring — paper trade to validate |",
        "| `LOW` | 1 | Single mention — note only |",
        "",
    ]

    # Group by confidence tier
    tiers = {"VERY HIGH": [], "HIGH": [], "MODERATE": [], "LOW": []}
    for concept, sources in sorted_concepts:
        n = len(sources)
        label = _confidence_label(n)
        supporting = _get_insights_for_concept(vault_dir, concept)
        tiers[label].append((concept, n, supporting))

    for tier in ["VERY HIGH", "HIGH", "MODERATE", "LOW"]:
        items = tiers[tier]
        if not items:
            continue
        lines += [f"## {tier} Confidence Rules", ""]
        for concept, n_sources, supporting in items:
            lines.append(f"### {concept.title()}")
            lines.append(f"_Confirmed by {n_sources} source(s) — confidence: `{tier}`_")
            lines.append("")
            if supporting:
                lines.append("**Supporting insights from vault:**")
                for s in supporting[:3]:
                    lines.append(f"- [{s['category']}] **{s['title']}**: {s['content'][:150]}...")
            lines += ["", "**Trade Rule (draft — validate before using):**",
                       f"_Define your specific rule for `{concept}` based on your ingested content._",
                       "", "---", ""]

    # Append insights by category
    for cat in ["rules", "patterns", "risk", "concepts", "psychology"]:
        rows = conn.execute(
            "SELECT i.title, i.content, s.source_type, s.title as src "
            "FROM insights i LEFT JOIN sources s ON i.source_id = s.id "
            "WHERE i.category = ? ORDER BY i.created_at DESC LIMIT 20",
            (cat,)
        ).fetchall()
        if rows:
            lines += [f"## {cat.title()} from Vault", ""]
            for r in rows:
                src_label = f"{r['source_type']}: {r['src'][:40]}" if r['src'] else "manual"
                lines += [
                    f"### {r['title']}",
                    r["content"],
                    f"_Source: {src_label}_",
                    "",
                ]

    lines += [
        "## Next Steps",
        "",
        "1. Review VERY HIGH and HIGH confidence concepts — these appear most consistently",
        "2. Define specific, testable entry/exit rules for each concept",
        "3. Backtest each rule individually on historical data",
        "4. Paper trade the combined strategy for at least 30 setups",
        "5. Review and iterate — re-run `--synthesize` after ingesting more sources",
        "",
        f"_Re-run synthesis: `python strategy_synthesizer.py --synthesize --vault-dir {vault_dir}`_",
    ]

    return "\n".join(lines)


def confidence_report(vault_dir: Path, json_output: bool = False):
    concept_sources = _scan_vault_sources(vault_dir)
    sorted_concepts = sorted(
        concept_sources.items(), key=lambda x: len(x[1]), reverse=True
    )
    report = [
        {"concept": c, "n_sources": len(s), "confidence": _confidence_label(len(s))}
        for c, s in sorted_concepts
    ]
    if json_output:
        print(json.dumps(report, indent=2))
    else:
        print("\n=== Concept Confidence Report ===")
        print(f"{'Concept':<30} {'Sources':>7} {'Confidence':>12}")
        print("-" * 52)
        for item in report:
            print(f"{item['concept']:<30} {item['n_sources']:>7} {item['confidence']:>12}")


def synthesize(vault_dir: Path, output: Optional[str] = None,
               instrument: str = "", timeframe: str = "",
               json_output: bool = False):
    print("Scanning vault...", file=sys.stderr)
    concept_sources = _scan_vault_sources(vault_dir)
    print(f"Found {len(concept_sources)} concepts across sources", file=sys.stderr)

    strategy = _build_strategy_document(vault_dir, concept_sources, instrument, timeframe)

    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(strategy, encoding="utf-8")
        print(f"✓ Strategy saved to: {output}")
    else:
        print(strategy)


def main():
    parser = argparse.ArgumentParser(description="Synthesize trading strategy from the vault.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--synthesize", action="store_true")
    group.add_argument("--confidence-report", action="store_true")
    group.add_argument("--sample", action="store_true")
    parser.add_argument("--vault-dir", default=str(VAULT_DIR_DEFAULT))
    parser.add_argument("--output", help="Save strategy to this file")
    parser.add_argument("--instrument", default="", help="e.g. 'ES futures', 'EURUSD'")
    parser.add_argument("--timeframe", default="", help="e.g. '15m', '1h'")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.sample:
        print(json.dumps([
            {"concept": "order block", "n_sources": 9, "confidence": "VERY HIGH"},
            {"concept": "fair value gap", "n_sources": 7, "confidence": "VERY HIGH"},
            {"concept": "risk reward", "n_sources": 12, "confidence": "VERY HIGH"},
            {"concept": "market structure", "n_sources": 6, "confidence": "HIGH"},
        ], indent=2))
        return

    vault_dir = Path(args.vault_dir)
    if args.synthesize:
        synthesize(vault_dir, output=args.output,
                   instrument=args.instrument, timeframe=args.timeframe,
                   json_output=args.json)
    elif args.confidence_report:
        confidence_report(vault_dir, json_output=args.json)


if __name__ == "__main__":
    main()
