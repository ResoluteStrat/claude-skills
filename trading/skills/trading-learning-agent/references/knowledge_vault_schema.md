# Knowledge Vault Schema Reference

## Purpose
Complete schema documentation for `~/.trading-vault/vault.db` — the SQLite database that indexes all ingested trading knowledge. This is the structural backbone of the second brain.

## Sources
1. SQLite FTS5 documentation — full-text search with `content=` tables and triggers
2. MemPalace architecture (resolutestrat/mempalace) — verbatim-first, local-first design
3. Niklas Luhmann, Zettelkasten method — cross-referenced index cards, each atomic, each linked
4. SQLite WAL mode documentation — concurrent read safety for long-running ingestors
5. Mark Pilgrim, *Dive Into Python 3* — stdlib-only philosophy for portability
6. Python `sqlite3` module docs — `detect_types`, `row_factory`, isolation levels

## Directory Layout

```
~/.trading-vault/
├── vault.db                    # SQLite database (all structured data)
├── sources/
│   ├── youtube/
│   │   └── <video_id>_<title>.md    # verbatim transcript
│   ├── discord/
│   │   └── <guild>_<channel>.md     # verbatim messages
│   └── platform/
│       └── <md5hash>_<title>.md     # verbatim course content
└── insights/
    ├── concepts.md             # exported insights by category
    ├── patterns.md
    ├── rules.md
    ├── risk.md
    └── psychology.md
```

## Table: `sources`

```sql
CREATE TABLE IF NOT EXISTS sources (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type  TEXT NOT NULL,        -- 'youtube' | 'discord' | 'platform'
    source_id    TEXT NOT NULL UNIQUE, -- video_id, channel_id, url_hash
    title        TEXT,
    url          TEXT,
    channel      TEXT,                 -- discord guild/channel name
    ingested_at  TEXT NOT NULL,        -- ISO 8601 UTC
    file_path    TEXT                  -- absolute path to verbatim .md file
);
```

### Constraints
- `source_id` is UNIQUE — re-ingesting the same video/channel is idempotent; the row is upserted, the file is overwritten
- `ingested_at` is always UTC ISO 8601: `2025-11-15T14:30:00Z`
- `file_path` must be absolute so the vault is portable across CWD changes

## Table: `insights`

```sql
CREATE TABLE IF NOT EXISTS insights (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id      INTEGER REFERENCES sources(id) ON DELETE CASCADE,
    category       TEXT NOT NULL,     -- concepts | patterns | rules | risk | psychology
    title          TEXT NOT NULL,
    content        TEXT NOT NULL,     -- verbatim or analyst-paraphrased observation
    tags           TEXT,              -- comma-separated: 'order block,ict,htf'
    confidence_raw INTEGER DEFAULT 0, -- n_sources at time of insertion
    created_at     TEXT NOT NULL
);
```

### Category Values
| Value | What it represents |
|---|---|
| `concepts` | Definitions, terminology |
| `patterns` | Recurring price setups |
| `rules` | Concrete entry/exit/sizing criteria |
| `risk` | Loss limits, position sizing, drawdown rules |
| `psychology` | Mindset, emotional management, execution discipline |

### Tags Convention
Comma-separated, lowercase, no spaces within a tag. Use canonical forms:
```
order block, fair value gap, market structure, kill zone,
liquidity, fibonacci, wyckoff, ict, smc, risk reward,
higher timeframe, lower timeframe, session, bias
```

## Virtual Table: `insights_fts` (FTS5)

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS insights_fts
USING fts5(
    title,
    content,
    tags,
    content='insights',
    content_rowid='id'
);
```

This is a **content table** — FTS5 does not store text itself; it indexes the `insights` table. Triggers keep them synchronized.

### Triggers

```sql
-- Keep FTS index in sync on INSERT
CREATE TRIGGER insights_ai AFTER INSERT ON insights BEGIN
    INSERT INTO insights_fts(rowid, title, content, tags)
    VALUES (new.id, new.title, new.content, new.tags);
END;

-- Keep FTS index in sync on DELETE
CREATE TRIGGER insights_ad AFTER DELETE ON insights BEGIN
    INSERT INTO insights_fts(insights_fts, rowid, title, content, tags)
    VALUES ('delete', old.id, old.title, old.content, old.tags);
END;
```

### FTS5 Query Syntax

```sql
-- Simple keyword match
SELECT i.* FROM insights i
JOIN insights_fts f ON f.rowid = i.id
WHERE insights_fts MATCH 'order block';

-- Prefix match
WHERE insights_fts MATCH 'liquidity*';

-- Boolean AND
WHERE insights_fts MATCH 'fvg AND kill zone';

-- Column-scoped
WHERE insights_fts MATCH 'tags:ict';
```

## Table: `pattern_occurrences`

```sql
CREATE TABLE IF NOT EXISTS pattern_occurrences (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_key TEXT NOT NULL,   -- canonical concept name (normalized)
    insight_id  INTEGER REFERENCES insights(id) ON DELETE CASCADE,
    source_id   INTEGER REFERENCES sources(id) ON DELETE CASCADE,
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pattern_key ON pattern_occurrences(pattern_key);
```

This table powers confidence scoring. Each time a concept appears in a new **independent source**, a row is inserted. The count of distinct `source_id` values per `pattern_key` is the confidence numerator.

## Indices

```sql
CREATE INDEX IF NOT EXISTS idx_insights_category ON insights(category);
CREATE INDEX IF NOT EXISTS idx_insights_source    ON insights(source_id);
CREATE INDEX IF NOT EXISTS idx_sources_type       ON sources(source_type);
```

## Connection Settings

All connections use:
```python
conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
conn.row_factory = sqlite3.Row
conn.execute('PRAGMA journal_mode=WAL')   # concurrent reads
conn.execute('PRAGMA foreign_keys=ON')    # cascade deletes
```

WAL mode allows concurrent readers while an ingestor is writing — important when `youtube_ingestor.py` runs a long playlist ingest while `knowledge_vault.py --search` is running in another terminal.

## Backup and Export

```bash
# SQLite hot backup (safe with WAL)
sqlite3 ~/.trading-vault/vault.db ".backup ~/.trading-vault/vault_backup_$(date +%Y%m%d).db"

# Export insights to markdown files for human review
python knowledge_vault.py --export-insights

# Stats snapshot
python knowledge_vault.py --stats
```

## Schema Evolution

Use `PRAGMA user_version` to track migrations:
```sql
PRAGMA user_version = 1;  -- set after initial schema creation
```
New columns use `ALTER TABLE ... ADD COLUMN` with a DEFAULT — SQLite supports this without a full rebuild.
