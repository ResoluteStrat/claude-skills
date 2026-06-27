---
name: cs:learn-discord
description: Harvest trading knowledge from a Discord channel export or live API. Filters for trading-relevant messages and stores verbatim. Use when the user provides a DiscordChatExporter JSON file or a channel ID with token.
---

# /cs:learn-discord

Harvest Discord channel content into `~/.trading-vault/` via `discord_harvester.py`.

## Pre-flight Gates

1. **Source provided** — refuse if neither `--export` file nor `--channel` + `--token` given
2. **Export file exists** — if using JSON export, verify file path is valid
3. **Token format** — if using API mode, token must be present (warn that user tokens violate Discord ToS; bot tokens are recommended)
4. **Vault accessible** — verify `~/.trading-vault/` exists or will be created

## Invocation

```bash
# From DiscordChatExporter JSON (recommended — no token needed)
python trading/skills/trading-learning-agent/scripts/discord_harvester.py \
  --export "/path/to/export.json" \
  --json

# From directory of exports (multiple channels)
python trading/skills/trading-learning-agent/scripts/discord_harvester.py \
  --export-dir "/path/to/exports/" \
  --json

# Live API (requires token)
python trading/skills/trading-learning-agent/scripts/discord_harvester.py \
  --channel "<CHANNEL_ID>" \
  --token "$DISCORD_TOKEN" \
  --limit 500 \
  --json

# Disable trading-keyword filter (keep all messages)
python trading/skills/trading-learning-agent/scripts/discord_harvester.py \
  --export export.json \
  --no-filter
```

## Filtering Logic

By default, only messages that meet at least one of these criteria are retained:
- Message is **pinned** in the channel
- Message body contains at least one **trading keyword** from the 40+ keyword list

Keywords include: `orderblock`, `fvg`, `liquidity`, `ict`, `smc`, `resistance`, `support`, `killzone`, `bias`, `htf`, `ltf`, `imbalance`, `sweep`, `reversal`, `structure`, `bos`, `choch`, and ~25 more.

Use `--no-filter` only when the entire channel is trading-focused and all messages are relevant.

## Post-harvest Report

```
✓ Harvested: The Trading Room → #setups-general
  Total messages: 1,847 | Trading-relevant: 234 (12.7%)
  Pinned messages included: 12
  Saved: ~/.trading-vault/sources/discord/TradingRoom_setups-general.md
  Source ID: 3
  Date range: 2025-10-01 to 2025-11-15
  Top concepts in messages: fvg (45 mentions), order block (38), liquidity (29),
                            nq (22), kill zone (18)
```

## DiscordChatExporter Setup

For users who don't have a bot token, recommend DiscordChatExporter:
```
https://github.com/Tyrrrz/DiscordChatExporter

Usage:
  DiscordChatExporter export -t USER_TOKEN -c CHANNEL_ID -f Json
```

The resulting `.json` file is passed directly to `--export`.
