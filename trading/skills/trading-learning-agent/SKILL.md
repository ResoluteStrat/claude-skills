---
name: trading-learning-agent
description: Use when you need to systematically ingest and learn from trading education content across YouTube videos, Discord channels, and online study platforms, retain everything in a structured second brain, and synthesize actionable strategies with calibrated confidence scores.
---

# Trading Learning Agent

## What This Skill Does

Automates the full learning pipeline for trading education:
1. **Ingest** — capture content verbatim from YouTube, Discord, learning platforms
2. **Retain** — store everything in a local SQLite + markdown knowledge vault
3. **Synthesize** — extract patterns, score confidence, build strategy documents
4. **Apply** — generate structured trading rules backed by source citations

This is the "second brain" layer that sits between consuming content and building a trading edge.

## Vault Structure

```
~/.trading-vault/
├── vault.db                    # SQLite database (FTS5 full-text search)
├── index.md                    # Compact AAAK-style index of all sources
├── sources/
│   ├── youtube/                # Verbatim transcripts + metadata
│   │   └── <video_id>_<title>.md
│   ├── discord/                # Channel exports (filtered for relevance)
│   │   └── <guild>_<channel>.md
│   └── platform/               # Course/lesson content
│       └── <slug>.md
├── insights/
│   ├── concepts.md             # Core trading concepts
│   ├── patterns.md             # Chart patterns + setups
│   ├── rules.md                # Entry/exit/filter rules
│   ├── risk.md                 # Risk management principles
│   └── psychology.md           # Trader mindset / discipline
└── strategies/
    └── strategy_v<n>.md        # Synthesized strategies with confidence
```

## Workflow

### Phase 1: Ingest Content

```bash
# YouTube video or playlist
python scripts/youtube_ingestor.py --url "https://youtube.com/watch?v=VIDEO_ID"
python scripts/youtube_ingestor.py --playlist "https://youtube.com/playlist?list=PL..."
python scripts/youtube_ingestor.py --file my_videos.txt   # batch file

# Discord channel (export via DiscordChatExporter)
python scripts/discord_harvester.py --export channel_export.json
python scripts/discord_harvester.py --export-dir ./exports/   # bulk

# Learning platform
python scripts/platform_scraper.py --url "https://platform.com/course/lesson-1"
python scripts/platform_scraper.py --url-file course_urls.txt
```

### Phase 2: Query the Vault

```bash
# Search across everything ingested
python scripts/knowledge_vault.py --search "order block"
python scripts/knowledge_vault.py --search "stop placement" --category rules

# Add a manual insight
python scripts/knowledge_vault.py --add-insight \
  --category patterns \
  --title "FVG Entry Setup" \
  --content "Fair value gaps on 15m form high-probability entries when price returns to fill during kill zone"

# Vault stats
python scripts/knowledge_vault.py --stats
```

### Phase 3: Synthesize Strategy

```bash
# Full strategy synthesis from vault
python scripts/strategy_synthesizer.py --synthesize

# Confidence report only
python scripts/strategy_synthesizer.py --confidence-report

# Export strategy to file
python scripts/strategy_synthesizer.py --synthesize --output ~/.trading-vault/strategies/strategy_v1.md
```

## Confidence Scale

Every synthesized rule carries a confidence rating based on how many independent sources confirm it:

| Level | Sources | Meaning |
|-------|---------|--------|
| `LOW` | 1 | Mentioned once — note but don't trade on it |
| `MODERATE` | 2–3 | Recurring across a few sources — worth paper trading |
| `HIGH` | 4–6 | Consistent across multiple independent sources — strong signal |
| `VERY HIGH` | 7+ | Universal agreement across vault — core principle |

## Prerequisites

- Python 3.10+ (stdlib only — no pip installs required for core features)
- `yt-dlp` (recommended, install via `pip install yt-dlp`) — for YouTube transcripts
- `playwright` (optional) — for JavaScript-heavy learning platforms

## Forcing Questions

Before running synthesis, answer these one at a time:

1. **Which sources have you ingested so far?** Run `--stats` to see. Synthesis with fewer than 5 sources produces LOW-confidence output only. Recommended answer: ingest at least 10 YouTube videos, 2+ Discord channels, and 1 course before first synthesis.

2. **What market/instrument are you focusing on?** The vault stores everything, but synthesis is most valuable when focused on a single instrument family (futures, forex, equities). Recommended answer: specify a primary instrument when calling `--synthesize --instrument "ES futures"`.

3. **What timeframe are you targeting?** Day trading (1m–15m), swing trading (1h–4h–Daily), or position trading? Recommended answer: specify with `--timeframe "15m"`.

4. **Are the sources you ingested from independent educators or one school/system?** Source diversity matters for confidence scoring. One school = one opinion. Recommended answer: ingest from at least 3 different educators/servers.

5. **How will you validate the synthesized strategy?** The vault builds knowledge; validation requires backtesting or paper trading. Recommended answer: define your validation method before treating any HIGH confidence rule as tradeable.

## References

- `references/trading_learning_methodology.md` — How to extract signal from noise in trading education content
- `references/knowledge_vault_schema.md` — Database schema and vault file format specification
- `references/strategy_synthesis_framework.md` — Confidence scoring algorithm and synthesis methodology

## Assets

- `assets/knowledge_entry_template.md` — Template for manual insight entries
- `assets/daily_digest_template.md` — End-of-day learning digest format
