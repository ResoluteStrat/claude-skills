---
name: cs:learn-yt
description: Ingest a YouTube video or playlist into the trading knowledge vault. Extracts transcript verbatim, detects trading concepts, and registers the source. Use when the user provides a YouTube URL to learn from.
---

# /cs:learn-yt

Ingest a YouTube video or playlist into `~/.trading-vault/` via `youtube_ingestor.py`.

## Pre-flight Gates

1. **URL provided** — refuse if no YouTube URL given
2. **yt-dlp available** — check `yt-dlp --version`; warn if missing (will use fallback API)
3. **Vault accessible** — verify `~/.trading-vault/` exists or will be created
4. **Not already ingested** — check `knowledge_vault.py --list-sources` for duplicate video ID

## Invocation

```bash
# Single video
python trading/skills/trading-learning-agent/scripts/youtube_ingestor.py \
  --url "<YOUTUBE_URL>" \
  --json

# Playlist (all videos)
python trading/skills/trading-learning-agent/scripts/youtube_ingestor.py \
  --playlist "<PLAYLIST_URL>" \
  --delay 2.0 \
  --json

# Batch from file (one URL per line)
python trading/skills/trading-learning-agent/scripts/youtube_ingestor.py \
  --file urls.txt \
  --delay 3.0
```

## Post-ingest Report

After successful ingest, surface to the user:
- Video title and duration
- Transcript chunk count and total word count
- File path saved to
- Key trading concepts detected (scan transcript for CORE_CONCEPTS keywords)
- Source ID assigned in vault.db
- Any errors or warnings (private video, no transcript, etc.)

## Example Output

```
✓ Ingested: "ICT 2022 Mentorship - Episode 14: Order Blocks"
  Duration: 1h 23m | Transcript: 847 chunks | ~12,400 words
  Saved: ~/.trading-vault/sources/youtube/dQw4w9WgXcQ_ICT_2022_Mentorship.md
  Source ID: 7
  Concepts detected: order block (23 mentions), kill zone (11), htf bias (8),
                     fair value gap (6), liquidity (5)
  
  Ready to add insights from this source? Run /cs:learn-yt or query the vault:
  python knowledge_vault.py --search "order block"
```

## Error Handling

- **Private/age-gated video**: Report clearly; do not attempt workarounds
- **No transcript available**: Ingest metadata only; note in source record that transcript is absent
- **yt-dlp not installed**: Fall back to timedtext API automatically; note in output
- **Duplicate source**: Confirm with user before re-ingesting (overwrites existing file)
