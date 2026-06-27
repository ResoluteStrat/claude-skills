#!/usr/bin/env python3
"""
discord_harvester.py — Parse Discord channel exports into the trading knowledge vault.

Primary mode: DiscordChatExporter JSON export (no token needed).
  Export tool: https://github.com/Tyrrrz/DiscordChatExporter

Secondary mode: Discord REST API with bot/user token (set DISCORD_TOKEN env var).

Usage:
    python discord_harvester.py --export channel_export.json [--vault-dir PATH] [--json]
    python discord_harvester.py --export-dir ./exports/
    python discord_harvester.py --channel CHANNEL_ID --token TOKEN
    python discord_harvester.py --sample
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

VAULT_DIR_DEFAULT = Path.home() / ".trading-vault"
DISCORD_API = "https://discord.com/api/v10"

TRADING_KEYWORDS = {
    "support", "resistance", "breakout", "setup", "entry", "exit", "stop",
    "target", "trend", "momentum", "volume", "price action", "candle",
    "pattern", "indicator", "strategy", "signal", "trade", "long", "short",
    "bull", "bear", "buy", "sell", "risk", "reward", "wick", "body",
    "consolidation", "range", "level", "zone", "ema", "sma", "rsi", "macd",
    "fibonacci", "fib", "orderblock", "ob", "fvg", "imbalance", "liquidity",
    "sweep", "ict", "smc", "wyckoff", "structure", "choch", "bos",
    "session", "london", "ny", "asia", "htf", "ltf", "confluence",
    "divergence", "overbought", "oversold", "breakeven", "r:r",
}


@dataclass
class DiscordMessage:
    message_id: str
    author: str
    timestamp: str
    content: str
    attachments: list
    embeds: list
    pinned: bool
    reactions: list


@dataclass
class ChannelMeta:
    channel_id: str
    channel_name: str
    guild_name: str
    topic: str
    message_count: int
    date_range: str


def _is_trading_relevant(msg: DiscordMessage) -> bool:
    if msg.pinned:
        return True
    if any("chart" in a["description"].lower() or "image" in a["description"].lower()
           for a in msg.attachments):
        return True
    content_lower = msg.content.lower()
    return any(kw in content_lower for kw in TRADING_KEYWORDS)


def _attachment_desc(a: dict) -> str:
    fname = a.get("fileName", a.get("filename", "")).lower()
    if any(fname.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]):
        return "[Chart/Image]"
    if fname.endswith((".mp4", ".mov")):
        return "[Video]"
    if fname.endswith(".pdf"):
        return "[PDF]"
    return f"[File: {fname or 'attachment'}]"


def _date_range(messages: list) -> str:
    ts = sorted(m.get("timestamp", "") for m in messages if m.get("timestamp"))
    if not ts:
        return "unknown"
    start, end = ts[0][:10], ts[-1][:10]
    return start if start == end else f"{start} to {end}"


def _parse_export(file_path: Path) -> tuple:
    data = json.loads(file_path.read_text(encoding="utf-8"))
    guild = data.get("guild", {})
    channel = data.get("channel", {})
    raw = data.get("messages", [])

    meta = ChannelMeta(
        channel_id=str(channel.get("id", "")),
        channel_name=channel.get("name", "unknown"),
        guild_name=guild.get("name", "unknown"),
        topic=channel.get("topic") or "",
        message_count=len(raw),
        date_range=_date_range(raw),
    )

    messages = []
    for m in raw:
        author = m.get("author", {})
        messages.append(DiscordMessage(
            message_id=str(m.get("id", "")),
            author=author.get("nickname") or author.get("name", "Unknown"),
            timestamp=m.get("timestamp", ""),
            content=m.get("content", ""),
            attachments=[
                {"filename": a.get("fileName", ""), "url": a.get("url", ""),
                 "description": _attachment_desc(a)}
                for a in m.get("attachments", [])
            ],
            embeds=[
                {"title": e.get("title", ""), "description": e.get("description", ""),
                 "url": e.get("url", "")}
                for e in m.get("embeds", [])
            ],
            pinned=m.get("isPinned", False),
            reactions=[
                {"emoji": r.get("emoji", {}).get("name", "?"), "count": r.get("count", 0)}
                for r in m.get("reactions", [])
            ],
        ))
    return meta, messages


def _api_request(endpoint: str, token: str) -> dict:
    token_str = token if token.startswith(("Bot ", "Bearer ")) else f"Bot {token}"
    req = urllib.request.Request(
        f"{DISCORD_API}{endpoint}",
        headers={
            "Authorization": token_str,
            "User-Agent": "TradingLearner (trading-skills, 1.0)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Discord API {e.code}: {e.read().decode()[:200]}")


def _fetch_via_api(channel_id: str, token: str, limit: int) -> tuple:
    chan = _api_request(f"/channels/{channel_id}", token)
    guild_name = "Unknown"
    if "guild_id" in chan:
        try:
            guild_name = _api_request(f"/guilds/{chan['guild_id']}", token).get("name", "Unknown")
        except RuntimeError:
            pass

    all_raw, before = [], None
    while len(all_raw) < limit:
        params = "?limit=100" + (f"&before={before}" if before else "")
        batch = _api_request(f"/channels/{channel_id}/messages{params}", token)
        if not batch:
            break
        all_raw.extend(batch)
        before = batch[-1]["id"]
        if len(batch) < 100:
            break
        time.sleep(0.5)

    meta = ChannelMeta(
        channel_id=channel_id,
        channel_name=chan.get("name", "unknown"),
        guild_name=guild_name,
        topic=chan.get("topic") or "",
        message_count=len(all_raw),
        date_range=_date_range(all_raw),
    )
    messages = []
    for m in all_raw:
        a = m.get("author", {})
        messages.append(DiscordMessage(
            message_id=str(m.get("id", "")),
            author=a.get("username", "Unknown"),
            timestamp=m.get("timestamp", ""),
            content=m.get("content", ""),
            attachments=[{"filename": att.get("filename", ""), "url": att.get("url", ""),
                          "description": _attachment_desc(att)} for att in m.get("attachments", [])],
            embeds=[{"title": e.get("title", ""), "description": e.get("description", ""),
                     "url": e.get("url", "")} for e in m.get("embeds", [])],
            pinned=m.get("pinned", False),
            reactions=[{"emoji": r.get("emoji", {}).get("name", "?"), "count": r.get("count", 0)}
                       for r in m.get("reactions", [])],
        ))
    return meta, messages


def _to_markdown(meta: ChannelMeta, messages: list) -> str:
    lines = [
        f"# Discord: #{meta.channel_name} — {meta.guild_name}",
        "",
        f"**Server:** {meta.guild_name}  ",
        f"**Channel:** #{meta.channel_name}  ",
        f"**Messages (trading-relevant):** {meta.message_count}  ",
        f"**Date Range:** {meta.date_range}  ",
        f"**Ingested:** {datetime.utcnow().isoformat()[:10]}  ",
        f"**Source Type:** Discord",
        "",
    ]
    if meta.topic:
        lines += [f"**Topic:** {meta.topic}", ""]

    pinned = [m for m in messages if m.pinned]
    if pinned:
        lines += ["## Pinned Messages", ""]
        for m in pinned:
            lines += _msg_lines(m)

    lines += ["## Messages", ""]
    for m in [m for m in messages if not m.pinned]:
        lines += _msg_lines(m)

    return "\n".join(lines)


def _msg_lines(m: DiscordMessage) -> list:
    ts = m.timestamp[:16].replace("T", " ") if m.timestamp else "?"
    lines = []
    if m.content or m.attachments or m.embeds:
        lines.append(f"**[{ts}] {m.author}**")
        if m.content:
            lines.append(m.content)
        for a in m.attachments:
            lines.append(f"  ↳ {a['description']} `{a['filename']}`")
        for e in m.embeds:
            if e["title"] or e["description"]:
                desc = (e["description"] or "")[:200]
                lines.append(f"  📎 **{e['title']}** {desc}")
        if m.reactions:
            rxn = " ".join(f"{r['emoji']}×{r['count']}" for r in m.reactions[:5])
            lines.append(f"  _{rxn}_")
        lines.append("")
    return lines


def _save(meta: ChannelMeta, content: str, vault_dir: Path) -> Path:
    dest = vault_dir / "sources" / "discord"
    dest.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w-]", "_", f"{meta.guild_name}_{meta.channel_name}")[:60]
    path = dest / f"{safe}.md"
    path.write_text(content, encoding="utf-8")

    index_path = vault_dir / "index.md"
    if not index_path.exists():
        index_path.write_text(
            "# Trading Knowledge Vault\n\n| Type | Date | Source | Title | ID |\n|------|------|--------|-------|-----|\n"
        )
    with index_path.open("a") as f:
        f.write(f"| Discord | {datetime.utcnow().isoformat()[:10]} | #{meta.channel_name}@{meta.guild_name} "
                f"| [{meta.channel_name}](sources/discord/{path.name}) | {meta.channel_id} |\n")
    return path


def harvest(meta: ChannelMeta, messages: list, vault_dir: Path,
            filter_relevant: bool, json_output: bool) -> dict:
    orig = len(messages)
    if filter_relevant:
        messages = [m for m in messages if _is_trading_relevant(m)]
    content = _to_markdown(
        ChannelMeta(meta.channel_id, meta.channel_name, meta.guild_name,
                    meta.topic, len(messages), meta.date_range),
        messages,
    )
    saved = _save(meta, content, vault_dir)
    result = {
        "channel": meta.channel_name, "guild": meta.guild_name,
        "total_messages": orig, "relevant_messages": len(messages),
        "date_range": meta.date_range, "saved_to": str(saved),
    }
    if json_output:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n✓ #{meta.channel_name} ({meta.guild_name})")
        print(f"  {len(messages)}/{orig} messages relevant | {meta.date_range}")
        print(f"  Saved: {saved}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Harvest Discord content into the trading vault.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--export", help="DiscordChatExporter JSON file")
    group.add_argument("--export-dir", help="Directory with multiple export JSON files")
    group.add_argument("--channel", help="Discord channel ID (needs --token)")
    group.add_argument("--sample", action="store_true")
    parser.add_argument("--token", help="Discord token (or DISCORD_TOKEN env var)")
    parser.add_argument("--vault-dir", default=str(VAULT_DIR_DEFAULT))
    parser.add_argument("--no-filter", action="store_true")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.sample:
        print(json.dumps({"channel": "trading-setups", "guild": "Pro Traders",
                          "total_messages": 3421, "relevant_messages": 1876,
                          "date_range": "2024-01-01 to 2025-06-01"}, indent=2))
        return

    vault_dir = Path(args.vault_dir)
    filter_on = not args.no_filter

    if args.export:
        meta, messages = _parse_export(Path(args.export))
        harvest(meta, messages, vault_dir, filter_on, args.json)
    elif args.export_dir:
        files = list(Path(args.export_dir).glob("*.json"))
        print(f"Processing {len(files)} exports...", file=sys.stderr)
        results = []
        for f in files:
            try:
                meta, messages = _parse_export(f)
                results.append(harvest(meta, messages, vault_dir, filter_on, False))
            except Exception as e:
                print(f"  Error {f.name}: {e}", file=sys.stderr)
        if args.json:
            print(json.dumps(results, indent=2))
    elif args.channel:
        token = args.token or os.environ.get("DISCORD_TOKEN")
        if not token:
            print("Need --token or DISCORD_TOKEN", file=sys.stderr)
            sys.exit(1)
        meta, messages = _fetch_via_api(args.channel, token, args.limit)
        harvest(meta, messages, vault_dir, filter_on, args.json)


if __name__ == "__main__":
    main()
