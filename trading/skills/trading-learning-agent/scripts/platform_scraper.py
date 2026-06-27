#!/usr/bin/env python3
"""
platform_scraper.py — Scrape trading education content from online learning platforms.

Auto-detects platform type and applies appropriate extraction strategy.
For JavaScript-rendered pages, invokes Playwright via subprocess if available.

Usage:
    python platform_scraper.py --url "https://platform.com/lesson" [--vault-dir PATH] [--json]
    python platform_scraper.py --url-file course_urls.txt [--vault-dir PATH]
    python platform_scraper.py --sample
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

VAULT_DIR_DEFAULT = Path.home() / ".trading-vault"

PLATFORM_PROFILES = {
    "udemy.com": {
        "name": "Udemy",
        "main_selectors": ["ud-component--course-taking--app", "lecture-view"],
        "title_pattern": r'"title":"([^"]{10,}?)"',
        "requires_js": True,
    },
    "coursera.org": {
        "name": "Coursera",
        "main_selectors": ["item-page-content"],
        "title_pattern": r'<title>([^<]+)</title>',
        "requires_js": True,
    },
    "teachable.com": {
        "name": "Teachable",
        "main_selectors": ["lecture-content", "course-lecture-page"],
        "title_pattern": r'<h1[^>]*>([^<]+)</h1>',
        "requires_js": False,
    },
    "thinkific.com": {
        "name": "Thinkific",
        "main_selectors": ["lesson-content", "content-container"],
        "title_pattern": r'<title>([^<]+)</title>',
        "requires_js": False,
    },
}


def _detect_platform(url: str) -> dict:
    for domain, profile in PLATFORM_PROFILES.items():
        if domain in url:
            return profile
    return {"name": "Generic", "main_selectors": [], "title_pattern": r'<title>([^<]+)</title>', "requires_js": False}


def _fetch_html(url: str, cookies: Optional[str] = None) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if cookies:
        headers["Cookie"] = cookies
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} for {url}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error for {url}: {e.reason}")


def _fetch_with_playwright(url: str) -> str:
    """Use Playwright CLI to render JS-heavy pages."""
    script = (
        "from playwright.sync_api import sync_playwright\n"
        "import sys\n"
        "with sync_playwright() as p:\n"
        "    b = p.chromium.launch(headless=True)\n"
        "    page = b.new_page()\n"
        f"    page.goto({repr(url)}, wait_until='networkidle', timeout=30000)\n"
        "    print(page.content())\n"
        "    b.close()\n"
    )
    try:
        result = subprocess.run(
            ["python", "-c", script],
            capture_output=True, text=True, timeout=45,
        )
        if result.returncode == 0:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ""


def _strip_html(html: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&#[0-9]+;', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _extract_main_content(html: str, profile: dict) -> str:
    """Try to extract the main content area using platform-specific selectors."""
    for selector in profile.get("main_selectors", []):
        pattern = f'(?:id|class)="[^"]*{re.escape(selector)}[^"]*"[^>]*>(.*?)</(?:div|section|article|main)'
        m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if m and len(m.group(1)) > 200:
            return _strip_html(m.group(1))

    # Fallback: try common content containers
    for tag in ["main", "article", r'div[^>]*class="[^"]*content[^"]*"']:
        m = re.search(f'<{tag}[^>]*>(.*?)</{tag.split("[")[0]}>', html, re.DOTALL | re.IGNORECASE)
        if m and len(m.group(1)) > 300:
            return _strip_html(m.group(1))

    return _strip_html(html)


def _extract_title(html: str, profile: dict) -> str:
    pattern = profile.get("title_pattern", r'<title>([^<]+)</title>')
    m = re.search(pattern, html)
    if m:
        return m.group(1).strip()[:200]
    return "Untitled Lesson"


def _extract_metadata(html: str) -> dict:
    """Extract OG/meta tags for additional context."""
    meta = {}
    for prop in ["og:title", "og:description", "og:site_name"]:
        m = re.search(f'property="{re.escape(prop)}"\s+content="([^"]+)"', html)
        if m:
            key = prop.replace("og:", "")
            meta[key] = m.group(1)[:500]
    return meta


def _format_content(url: str, title: str, platform_name: str,
                   content: str, metadata: dict) -> str:
    lines = [
        f"# {title}",
        "",
        f"**URL:** {url}",
        f"**Platform:** {platform_name}",
        f"**Ingested:** {datetime.utcnow().isoformat()[:10]}",
        f"**Source Type:** Learning Platform",
        "",
    ]
    if metadata.get("description"):
        lines += [f"**Description:** {metadata['description']}", ""]
    lines += ["## Content", "", content, ""]
    return "\n".join(lines)


def _save(url: str, title: str, content: str, vault_dir: Path) -> Path:
    dest = vault_dir / "sources" / "platform"
    dest.mkdir(parents=True, exist_ok=True)
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    safe_title = re.sub(r"[^\w-]", "_", title)[:50]
    path = dest / f"{url_hash}_{safe_title}.md"
    path.write_text(content, encoding="utf-8")

    index_path = vault_dir / "index.md"
    if not index_path.exists():
        index_path.write_text(
            "# Trading Knowledge Vault\n\n| Type | Date | Source | Title | ID |\n|------|------|--------|-------|-----|\n"
        )
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    with index_path.open("a") as f:
        f.write(f"| Platform | {datetime.utcnow().isoformat()[:10]} | {domain} "
                f"| [{title[:40]}](sources/platform/{path.name}) | {url_hash} |\n")
    return path


def scrape_url(url: str, vault_dir: Path, cookies: Optional[str] = None,
               json_output: bool = False) -> dict:
    profile = _detect_platform(url)
    print(f"  Platform: {profile['name']} | URL: {url[:80]}", file=sys.stderr)

    html = ""
    if profile.get("requires_js"):
        print(f"  Trying Playwright for JS-rendered content...", file=sys.stderr)
        html = _fetch_with_playwright(url)

    if not html:
        print(f"  Fetching HTML...", file=sys.stderr)
        html = _fetch_html(url, cookies=cookies)

    title = _extract_title(html, profile)
    metadata = _extract_metadata(html)
    content = _extract_main_content(html, profile)

    # Quality check
    if len(content) < 100:
        print(f"  Warning: very little content extracted ({len(content)} chars). "
              f"Page may require login or JS rendering.", file=sys.stderr)

    formatted = _format_content(url, title, profile['name'], content, metadata)
    saved = _save(url, title, formatted, vault_dir)

    result = {
        "url": url,
        "platform": profile['name'],
        "title": title,
        "content_length": len(content),
        "saved_to": str(saved),
    }
    if json_output:
        print(json.dumps(result, indent=2))
    else:
        print(f"  ✓ {title} ({len(content):,} chars) → {saved.name}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Scrape learning platform content into the trading vault.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="Single lesson/page URL")
    group.add_argument("--url-file", help="Text file with one URL per line")
    group.add_argument("--sample", action="store_true")
    parser.add_argument("--vault-dir", default=str(VAULT_DIR_DEFAULT))
    parser.add_argument("--cookies", help="Cookie string for authenticated pages")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay between requests")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.sample:
        print(json.dumps({"url": "https://school.com/trading/lesson-1",
                          "platform": "Generic", "title": "Understanding Market Structure",
                          "content_length": 4823, "saved_to": "~/.trading-vault/sources/platform/abc12345_Understanding_Market_Structure.md"}, indent=2))
        return

    vault_dir = Path(args.vault_dir)
    if args.url:
        scrape_url(args.url, vault_dir, cookies=args.cookies, json_output=args.json)
    elif args.url_file:
        urls = [l.strip() for l in Path(args.url_file).read_text().splitlines()
                if l.strip() and not l.startswith("#")]
        results = []
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}]", file=sys.stderr)
            try:
                results.append(scrape_url(url, vault_dir, cookies=args.cookies))
            except Exception as e:
                print(f"  Error: {e}", file=sys.stderr)
                results.append({"url": url, "error": str(e)})
            if i < len(urls):
                time.sleep(args.delay)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            ok = sum(1 for r in results if "error" not in r)
            print(f"\n✓ {ok}/{len(results)} pages scraped")


if __name__ == "__main__":
    main()
