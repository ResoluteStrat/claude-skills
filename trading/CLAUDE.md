# trading/CLAUDE.md

**Trading Learning Agent** — automated multi-source content ingestion and knowledge synthesis system. Ingests YouTube videos, Discord channels, and online learning platforms; retains everything verbatim in a local SQLite + markdown second brain (`~/.trading-vault/`); synthesizes confidence-scored trading strategies from accumulated knowledge.

## Domain Purpose

This is NOT a trading execution system. It is a **knowledge acquisition and synthesis engine** for traders who want to learn systematically from multiple content sources and build evidence-based trading strategies.

## Architecture

```
Content Sources          Ingestors              Knowledge Vault
──────────────          ──────────             ───────────────
YouTube URLs    →  youtube_ingestor.py  →  ~/.trading-vault/
Discord exports →  discord_harvester.py →  vault.db (SQLite + FTS5)
Platform URLs   →  platform_scraper.py  →  sources/*.md (verbatim)
                                           insights/*.md
                                           index.md (compact)
                                                ↓
                                   knowledge_vault.py (R/W API)
                                                ↓
                                   strategy_synthesizer.py
                                                ↓
                                   strategies/strategy_vN.md
```

## Scripts

| Script | Purpose | Key Flags |
|--------|---------|----------|
| `youtube_ingestor.py` | Extract YT transcripts + chapters | `--url`, `--playlist`, `--file` |
| `discord_harvester.py` | Parse Discord exports + API | `--export`, `--export-dir`, `--channel` |
| `platform_scraper.py` | Scrape learning platforms | `--url`, `--url-file`, `--platform` |
| `knowledge_vault.py` | Second brain R/W API | `--search`, `--add-insight`, `--stats` |
| `strategy_synthesizer.py` | Build strategies from vault | `--synthesize`, `--confidence-report` |

## Commands

- `/cs:learn-yt <url>` — Ingest YouTube video or playlist
- `/cs:learn-discord <export_file>` — Process Discord channel export
- `/cs:learn-platform <url>` — Scrape learning platform content
- `/cs:digest-day` — End-of-day synthesis and knowledge update
- `/cs:build-strategy` — Synthesize vault into a trading strategy document

## Hard Rules

1. **Verbatim always** — Raw content stored exactly as captured; synthesis never overwrites source
2. **Source-tagged** — Every insight tracks its origin (URL, timestamp, channel)
3. **Confidence-explicit** — Every rule shows `n_sources` (how many independent sources agree)
4. **No fabrication** — Strategy rules emerge only from actual ingested content
5. **Local-first** — All data in `~/.trading-vault/`; nothing sent to external services by default
