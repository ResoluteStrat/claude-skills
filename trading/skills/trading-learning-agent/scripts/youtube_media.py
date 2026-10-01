#!/usr/bin/env python3
"""
youtube_media.py — Full video capture: Whisper transcript (when no captions) + full-resolution
scene-change screenshots, saved verbatim into the vault.

Needs: yt-dlp, ffmpeg, faster-whisper (only for caption-less videos).
YouTube blocks datacenter IPs ("Sign in to confirm you're not a bot"). Fixes, in order:
  1. --cookies cookies.txt  (Netscape format exported from a logged-in browser; never commit it)
  2. a PO-token server (pip install bgutil-ytdlp-pot-provider; run its server on :4416)
  3. run this script from a residential IP (your own computer)

Usage:
    python youtube_media.py --url URL --vault-dir PATH [--cookies cookies.txt]
    python youtube_media.py --playlist URL --vault-dir PATH --cookies cookies.txt
    python youtube_media.py --local video.mp4 --vault-dir PATH      # already-downloaded file
Output (per video id):
    <vault>/sources/youtube/media/<id>/frame_0001_<mm-ss>.jpg ... and frames.md
    <vault>/sources/youtube/whisper/<id>.txt   (only if no captions)
"""

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

YTDLP = [sys.executable, "-m", "yt_dlp"]
VAULT_DEFAULT = Path.home() / ".trading-vault"


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def download(url: str, out_dir: Path, cookies: str = "") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [*YTDLP, "-f", "bv*[height<=720]+ba/b[height<=720]/b", "--merge-output-format", "mp4",
           "-o", str(out_dir / "%(id)s.%(ext)s"), "--sleep-requests", "1", url]
    if cookies:
        cmd[len(YTDLP):len(YTDLP)] = ["--cookies", cookies]
    vid = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url).group(1)
    target = out_dir / f"{vid}.mp4"
    for attempt in range(3):
        r = _run(cmd)
        if target.exists():
            return target
        time.sleep(30 * (attempt + 1))
    raise RuntimeError(f"download failed: {r.stderr.strip().splitlines()[-1] if r.stderr else 'unknown'}")


def extract_frames(video: Path, out_dir: Path, scene: float = 0.06, min_gap: int = 8) -> list:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in list(out_dir.glob("raw_*.jpg")) + list(out_dir.glob("frame_*.jpg")):
        old.unlink()
    pattern = out_dir / "raw_%05d.jpg"
    vf = f"select='gt(scene,{scene})+isnan(prev_selected_t)+gte(t-prev_selected_t,60)',showinfo"
    r = _run(["ffmpeg", "-v", "info", "-y", "-i", str(video), "-vf", vf, "-fps_mode", "vfr",
              "-q:v", "3", str(pattern)])
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + " ".join(r.stderr.strip().splitlines()[-3:]))
    times = [float(m.group(1)) for m in re.finditer(r"pts_time:([\d.]+)", r.stderr)]
    frames, last = [], -1e9
    for i, raw in enumerate(sorted(out_dir.glob("raw_*.jpg"))):
        t = times[i] if i < len(times) else 0.0
        if t - last < min_gap:
            raw.unlink()
            continue
        last = t
        final = out_dir / f"frame_{len(frames)+1:04d}_{int(t)//60:02d}-{int(t)%60:02d}.jpg"
        raw.replace(final)
        frames.append((t, final.name))
    lines = [f"# Frames: {video.stem}\n", "| Time | File |", "|---|---|"]
    lines += [f"| {int(t)//60}:{int(t)%60:02d} | {n} |" for t, n in frames]
    (out_dir / "frames.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return frames


def whisper_transcript(video: Path, out_file: Path, model: str = "small") -> int:
    from faster_whisper import WhisperModel
    segs, _ = WhisperModel(model, device="cpu", compute_type="int8").transcribe(str(video), vad_filter=True)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_file.open("w", encoding="utf-8") as f:
        for s in segs:
            f.write(f"`{int(s.start)//60}:{int(s.start)%60:02d}` {s.text.strip()}\n")
            n += 1
    return n


def process(video: Path, vault: Path, need_whisper: bool, model: str):
    vid = video.stem
    base = vault / "sources" / "youtube"
    frames = extract_frames(video, base / "media" / vid)
    res = {"video_id": vid, "frames": len(frames)}
    if need_whisper:
        res["whisper_segments"] = whisper_transcript(video, base / "whisper" / f"{vid}.txt", model)
    return res


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--url")
    g.add_argument("--playlist")
    g.add_argument("--local")
    p.add_argument("--vault-dir", default=str(VAULT_DEFAULT))
    p.add_argument("--cookies", default="")
    p.add_argument("--whisper", action="store_true", help="transcribe audio (use when no captions)")
    p.add_argument("--model", default="small")
    a = p.parse_args()
    vault = Path(a.vault_dir).expanduser()
    if a.local:
        print(process(Path(a.local), vault, a.whisper, a.model))
        return
    if a.playlist:
        ids = _run([*YTDLP, "--flat-playlist", "--print", "%(id)s", a.playlist]).stdout.split()
        urls = [f"https://youtu.be/{i}" for i in ids]
    else:
        urls = [a.url]
    tmp = vault / "sources" / "youtube" / "_video_cache"
    for u in urls:
        try:
            video = download(u, tmp, a.cookies)
            print(process(video, vault, a.whisper, a.model))
        except Exception as e:
            print({"url": u, "error": str(e)}, file=sys.stderr)
        time.sleep(10)


if __name__ == "__main__":
    main()
