#!/usr/bin/env python3
"""
youtube_frames.py — Capture timestamped screenshot frames of YouTube videos into the vault.

Uses YouTube's storyboard sprite sheets (i.ytimg.com), which stay reachable when the
video stream itself is blocked. Frames are 320x180: enough for candle structure, zones
and drawn levels, not for small on-screen text (use the transcript for that).

Requires: yt-dlp, ffmpeg.

Usage:
    python youtube_frames.py --url URL [--vault-dir PATH]
    python youtube_frames.py --playlist URL [--vault-dir PATH] [--delay 8]
    python youtube_frames.py --file urls.txt
Output: <vault>/sources/youtube/frames/<video_id>/sheet_NN.png (3x3 contact sheets,
        labelled by start time) and frames/<video_id>/index.md (time -> frame file).
"""

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

VAULT_DIR_DEFAULT = Path.home() / ".trading-vault"
CLIENT_ARGS = ["--extractor-args", "youtube:player_client=web,mweb"]


def _video_id(url: str):
    m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def _storyboard(video_id: str):
    cmd = ["yt-dlp", "-j", "-f", "sb0", *CLIENT_ARGS, f"https://youtu.be/{video_id}"]
    for attempt in range(4):
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.stdout.strip():
            d = json.loads(r.stdout)
            frags = d.get("fragments") or d["requested_formats"][0]["fragments"]
            return d, frags
        time.sleep(15 * (attempt + 1))
    return None, []


def capture(video_id: str, vault_dir: Path) -> dict:
    info, frags = _storyboard(video_id)
    if not frags:
        return {"video_id": video_id, "frames": 0, "error": "no storyboard (rate-limited?)"}
    rows, cols = info.get("rows", 3), info.get("columns", 3)
    out = vault_dir / "sources" / "youtube" / "frames" / video_id
    out.mkdir(parents=True, exist_ok=True)
    lines = [f"# Frames: {info.get('title', video_id)}\n",
             f"Video: https://youtu.be/{video_id}  (320x180 storyboard frames)\n",
             "| Sheet | Start | End | File |", "|---|---|---|---|"]
    t, n = 0.0, 0
    for i, fr in enumerate(frags):
        raw = out / f"sheet_{i:02d}.webp"
        with urllib.request.urlopen(fr["url"], timeout=60) as resp:
            raw.write_bytes(resp.read())
        png = out / f"sheet_{i:02d}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), str(png)], check=True)
        raw.unlink()
        dur = float(fr["duration"])
        lines.append(f"| {i} | {int(t)//60}:{int(t)%60:02d} | "
                     f"{int(t+dur)//60}:{int(t+dur)%60:02d} | {png.name} |")
        t += dur
        n += rows * cols
    (out / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"video_id": video_id, "frames": n, "sheets": len(frags), "dir": str(out)}


def _playlist_ids(url: str) -> list:
    r = subprocess.run(["yt-dlp", "--flat-playlist", "--print", "%(id)s", url],
                       capture_output=True, text=True, timeout=120)
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--url")
    g.add_argument("--playlist")
    g.add_argument("--file")
    p.add_argument("--vault-dir", default=str(VAULT_DIR_DEFAULT))
    p.add_argument("--delay", type=float, default=8)
    a = p.parse_args()
    if a.url:
        ids = [_video_id(a.url)]
    elif a.playlist:
        ids = _playlist_ids(a.playlist)
    else:
        ids = [_video_id(l) for l in Path(a.file).read_text().splitlines() if l.strip()]
    ok = 0
    for i, vid in enumerate(filter(None, ids)):
        res = capture(vid, Path(a.vault_dir).expanduser())
        print(json.dumps(res))
        ok += bool(res.get("frames"))
        time.sleep(a.delay)
    print(f"Captured frames for {ok}/{len(ids)} videos")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
