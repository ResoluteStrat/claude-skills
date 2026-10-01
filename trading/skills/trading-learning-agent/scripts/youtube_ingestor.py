#!/usr/bin/env python3
"""
youtube_ingestor.py — Extract YouTube video transcripts and metadata into the trading knowledge vault.

Uses yt-dlp (if installed) for transcript extraction, with fallback to YouTube's
timedtext API for auto-generated captions.

Usage:
    python youtube_ingestor.py --url "https://youtube.com/watch?v=VIDEO_ID" [--vault-dir PATH] [--json]
    python youtube_ingestor.py --playlist "https://youtube.com/playlist?list=PL..."
    python youtube_ingestor.py --file urls.txt
    python youtube_ingestor.py --sample
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


YTDLP = [sys.executable, "-m", "yt_dlp"]
VAULT_DIR_DEFAULT = Path.home() / ".trading-vault"


@dataclass
class VideoMeta:
    video_id: str
    title: str
    description: str
    channel: str
    duration_seconds: int
    url: str
    chapters: list
    ingest_ts: str


@dataclass
class TranscriptChunk:
    start_seconds: float
    text: str


def _extract_video_id(url: str) -> Optional[str]:
    patterns = [
        r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})",
        r"embed/([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def _fetch_page(url: str, timeout: int = 15) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; TradingLearner/1.0)",
        "Accept-Language": "en-US,en;q=0.9",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def _meta_from_page(video_id: str) -> VideoMeta:
    """Extract title/description/channel from the YouTube watch page."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    html = _fetch_page(url)

    title_m = re.search(r'"title":\{"runs":\[\{"text":"([^"]+)"', html)
    title = title_m.group(1) if title_m else f"Video {video_id}"

    channel_m = re.search(r'"ownerChannelName":"([^"]+)"', html)
    channel = channel_m.group(1) if channel_m else "Unknown"

    desc_m = re.search(r'"shortDescription":"((?:[^"\\]|\\.)*)"', html)
    description = ""
    if desc_m:
        description = desc_m.group(1).replace("\\n", "\n").replace('\\"', '"')

    duration_m = re.search(r'"lengthSeconds":"(\d+)"', html)
    duration = int(duration_m.group(1)) if duration_m else 0

    chapters = _parse_chapters_from_description(description)

    return VideoMeta(
        video_id=video_id,
        title=title,
        channel=channel,
        description=description[:2000],
        duration_seconds=duration,
        url=f"https://youtube.com/watch?v={video_id}",
        chapters=chapters,
        ingest_ts=datetime.utcnow().isoformat(),
    )


def _parse_chapters_from_description(description: str) -> list:
    pattern = re.compile(
        r"(?:^|\n)([0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)\s+(.+)", re.MULTILINE
    )
    return [
        {"timestamp": m.group(1), "title": m.group(2).strip()}
        for m in pattern.finditer(description)
    ]


def _transcript_via_ytdlp(video_id: str, tmp_dir: str) -> list:
    url = f"https://www.youtube.com/watch?v={video_id}"
    out_template = os.path.join(tmp_dir, "%(id)s")
    cmd = [
        *YTDLP,
        "--skip-download",
        "--write-auto-sub",
        "--write-sub",
        "--sub-langs", "en.*,en",
        "--sub-format", "vtt",
        "--output", out_template,
        "--quiet",
        url,
    ]
    for attempt in range(4):
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except FileNotFoundError:
            return []
        except subprocess.TimeoutExpired:
            pass
        vtt_files = list(Path(tmp_dir).glob(f"{video_id}*.vtt"))
        if vtt_files:
            best = max(vtt_files, key=lambda p: p.stat().st_size)
            return _parse_vtt(best.read_text(encoding="utf-8"))
        time.sleep(15 * (attempt + 1))  # back off on YouTube 429 rate limits
    return []


def _parse_vtt(vtt_content: str) -> list:
    chunks = []
    lines = vtt_content.splitlines()
    i = 0
    while i < len(lines):
        ts_match = re.match(
            r"(\d+:\d+:\d+\.\d+|\d+:\d+\.\d+)\s+-->\s+", lines[i].strip()
        )
        if ts_match:
            start_seconds = _vtt_ts_to_seconds(ts_match.group(1))
            text_lines = []
            i += 1
            while i < len(lines) and lines[i].strip():
                txt = re.sub(r"<[^>]+>", "", lines[i]).strip()
                if txt:
                    text_lines.append(txt)
                i += 1
            if text_lines:
                chunks.append(TranscriptChunk(
                    start_seconds=start_seconds,
                    text=" ".join(text_lines),
                ))
        else:
            i += 1
    return _deduplicate_transcript(chunks)


def _vtt_ts_to_seconds(ts: str) -> float:
    parts = ts.replace(",", ".").split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    return float(parts[0]) * 60 + float(parts[1])


def _transcript_via_timedtext_api(video_id: str) -> list:
    list_url = f"https://www.youtube.com/api/timedtext?type=list&v={video_id}"
    try:
        list_xml = _fetch_page(list_url, timeout=10)
    except Exception:
        return []
    lang_match = re.search(r'lang_code="(en[^"]*)"', list_xml)
    lang = lang_match.group(1) if lang_match else "en"
    ts_url = (
        f"https://www.youtube.com/api/timedtext"
        f"?v={video_id}&lang={lang}&fmt=json3&xorb=2&xobt=3&xovt=3"
    )
    try:
        ts_data = _fetch_page(ts_url, timeout=15)
        data = json.loads(ts_data)
    except Exception:
        return []
    chunks = []
    for event in data.get("events", []):
        if "segs" not in event:
            continue
        start_ms = event.get("tStartMs", 0)
        text = "".join(s.get("utf8", "") for s in event["segs"]).strip()
        if text and text != "\n":
            chunks.append(TranscriptChunk(
                start_seconds=start_ms / 1000.0,
                text=text.replace("\n", " "),
            ))
    return _deduplicate_transcript(chunks)


def _deduplicate_transcript(chunks: list) -> list:
    result, prev = [], ""
    for c in chunks:
        if c.text.strip() and c.text.strip() != prev:
            result.append(c)
            prev = c.text.strip()
    return result


def _seconds_to_hhmmss(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def _format_content(meta: VideoMeta, chunks: list) -> str:
    lines = [
        f"# {meta.title}",
        "",
        f"**Channel:** {meta.channel}",
        f"**URL:** {meta.url}",
        f"**Duration:** {meta.duration_seconds // 60}m {meta.duration_seconds % 60}s",
        f"**Ingested:** {meta.ingest_ts[:10]}",
        f"**Source Type:** YouTube",
        "",
    ]
    if meta.description:
        lines += ["## Description", "", meta.description[:1000], ""]
    if meta.chapters:
        lines += ["## Chapters", ""]
        for ch in meta.chapters:
            lines.append(f"- `{ch['timestamp']}` {ch['title']}")
        lines.append("")
    lines += ["## Transcript", ""]
    if chunks:
        for chunk in chunks:
            ts = _seconds_to_hhmmss(chunk.start_seconds)
            lines.append(f"`{ts}` {chunk.text}")
    else:
        lines.append("_No transcript available — video may be private, age-restricted, or have no captions._")
    return "\n".join(lines)


def _save_to_vault(meta: VideoMeta, content: str, vault_dir: Path) -> Path:
    sources_dir = vault_dir / "sources" / "youtube"
    sources_dir.mkdir(parents=True, exist_ok=True)
    safe_title = re.sub(r"[^\w\s-]", "", meta.title)[:50].strip().replace(" ", "_")
    file_path = sources_dir / f"{meta.video_id}_{safe_title}.md"
    file_path.write_text(content, encoding="utf-8")
    _update_index(vault_dir, "YT", meta.ingest_ts[:10], meta.channel,
                  meta.title[:40], f"sources/youtube/{file_path.name}", meta.video_id)
    sys.path.insert(0, str(Path(__file__).parent))
    import knowledge_vault
    conn = knowledge_vault._get_db(vault_dir)
    known = conn.execute("SELECT 1 FROM sources WHERE source_type='youtube' AND source_id=?",
                         (meta.video_id,)).fetchone()
    conn.close()
    if not known:
        knowledge_vault.register_source(vault_dir, "youtube", meta.video_id, meta.title,
                                        url=meta.url, channel=meta.channel,
                                        file_path=str(file_path))
    return file_path


def _update_index(vault_dir: Path, src_type: str, date: str, source: str,
                  title: str, rel_path: str, id_: str):
    index_path = vault_dir / "index.md"
    if not index_path.exists():
        index_path.write_text(
            "# Trading Knowledge Vault\n\n"
            "| Type | Date | Source | Title | ID |\n"
            "|------|------|--------|-------|-----|\n",
            encoding="utf-8",
        )
    with index_path.open("a", encoding="utf-8") as f:
        f.write(f"| {src_type} | {date} | {source} | [{title}]({rel_path}) | {id_} |\n")


def ingest_video(url: str, vault_dir: Path, json_output: bool = False) -> dict:
    video_id = _extract_video_id(url)
    if not video_id:
        raise ValueError(f"Cannot extract video ID from: {url}")
    print(f"  Fetching metadata: {video_id}", file=sys.stderr)
    meta = _meta_from_page(video_id)
    print(f"  Extracting transcript...", file=sys.stderr)
    chunks = []
    with tempfile.TemporaryDirectory() as tmp:
        chunks = _transcript_via_ytdlp(video_id, tmp)
    if not chunks:
        chunks = _transcript_via_timedtext_api(video_id)
    content = _format_content(meta, chunks)
    saved_path = _save_to_vault(meta, content, vault_dir)
    result = {
        "video_id": meta.video_id,
        "title": meta.title,
        "channel": meta.channel,
        "duration_seconds": meta.duration_seconds,
        "transcript_chunks": len(chunks),
        "chapters_found": len(meta.chapters),
        "saved_to": str(saved_path),
    }
    if json_output:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n✓ {meta.title}")
        print(f"  Channel: {meta.channel} | Duration: {meta.duration_seconds//60}m")
        print(f"  Transcript: {len(chunks)} chunks | Chapters: {len(meta.chapters)}")
        print(f"  Saved: {saved_path}")
    return result


def ingest_playlist(playlist_url: str, vault_dir: Path, delay: float = 2.0) -> list:
    cmd = [*YTDLP, "--flat-playlist", "--print", "url", playlist_url, "--quiet"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        urls = [u.strip() for u in result.stdout.splitlines() if u.strip()]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("yt-dlp not found — cannot list playlist.", file=sys.stderr)
        return []
    results = []
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] {url}", file=sys.stderr)
        try:
            results.append(ingest_video(url, vault_dir))
        except Exception as e:
            results.append({"url": url, "error": str(e)})
        if i < len(urls):
            time.sleep(delay)
    return results


def main():
    parser = argparse.ArgumentParser(description="Ingest YouTube videos into the trading vault.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="Single YouTube URL")
    group.add_argument("--playlist", help="YouTube playlist URL")
    group.add_argument("--file", help="Text file with one URL per line")
    group.add_argument("--sample", action="store_true")
    parser.add_argument("--vault-dir", default=str(VAULT_DIR_DEFAULT))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args()

    if args.sample:
        print(json.dumps({
            "video_id": "abc123", "title": "ICT Order Blocks Explained",
            "channel": "Trading Education", "duration_seconds": 1847,
            "transcript_chunks": 423, "chapters_found": 8,
            "saved_to": str(VAULT_DIR_DEFAULT / "sources/youtube/abc123_ICT_Order_Blocks.md"),
        }, indent=2))
        return

    vault_dir = Path(args.vault_dir)
    if args.url:
        ingest_video(args.url, vault_dir, json_output=args.json)
    elif args.playlist:
        results = ingest_playlist(args.playlist, vault_dir, delay=args.delay)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\n✓ Ingested {sum(1 for r in results if 'error' not in r)}/{len(results)} videos")
    elif args.file:
        urls = [l.strip() for l in Path(args.file).read_text().splitlines()
                if l.strip() and not l.startswith("#")]
        results = []
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] {url}", file=sys.stderr)
            try:
                results.append(ingest_video(url, vault_dir))
            except Exception as e:
                results.append({"url": url, "error": str(e)})
            time.sleep(1.5)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\n✓ {sum(1 for r in results if 'error' not in r)}/{len(results)} succeeded")


if __name__ == "__main__":
    main()
