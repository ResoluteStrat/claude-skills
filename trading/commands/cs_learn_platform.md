---
name: cs:learn-platform
description: Scrape a trading course or lesson page from an online learning platform into the knowledge vault. Handles JS-heavy platforms via Playwright. Use when the user provides a URL to a course, lesson, or study material page.
---

# /cs:learn-platform

Scrape online learning platform content into `~/.trading-vault/` via `platform_scraper.py`.

## Pre-flight Gates

1. **URL provided** — refuse if no URL given
2. **Platform detected** — identify the platform (Udemy, Coursera, Teachable, Thinkific, or generic)
3. **Access check** — for platforms requiring login, confirm cookies file is provided or user is logged in
4. **Playwright available** — for JS-heavy platforms, check `playwright --version`; warn if missing

## Invocation

```bash
# Single page
python trading/skills/trading-learning-agent/scripts/platform_scraper.py \
  --url "<COURSE_PAGE_URL>" \
  --json

# Multiple URLs from file (one per line)
python trading/skills/trading-learning-agent/scripts/platform_scraper.py \
  --url-file lesson_urls.txt \
  --delay 3.0

# With browser cookies for authenticated content
python trading/skills/trading-learning-agent/scripts/platform_scraper.py \
  --url "<URL>" \
  --cookies "/path/to/cookies.json"
```

## Platform-Specific Notes

| Platform | JS Required | Auth Needed | Notes |
|---|---|---|---|
| Udemy | Yes (Playwright) | Yes | Must be enrolled; export cookies from browser |
| Coursera | Yes (Playwright) | Yes | Free audit may limit content |
| Teachable | No | Sometimes | Depends on course settings |
| Thinkific | No | Sometimes | Depends on course settings |
| Generic | Auto-detected | Varies | Falls back to plain HTTP |

## Cookie Export

For authenticated platforms, export cookies using a browser extension:
- Chrome/Firefox: "Export Cookies" or "Cookie Quick Manager"
- Export as JSON (Netscape format also accepted)
- Pass path to `--cookies`

## Post-scrape Report

```
✓ Scraped: "Module 3: Market Structure and Order Blocks" (Teachable)
  Platform: Teachable (static HTML)
  Content: 4,821 words extracted
  Saved: ~/.trading-vault/sources/platform/a3f8b2c1_Module_3_Market_Structure.md
  Source ID: 5
  Concepts detected: market structure (18 mentions), order block (14), bos (9),
                     choch (7), premium discount (5)

  ⚠ No Playwright available — used requests fallback (some dynamic content may be missing)
```

## Installing Playwright (if needed)

```bash
pip install playwright
playwright install chromium
```

For courses behind video players (Vimeo embed, Wistia, etc.), the scraper captures the surrounding transcript/notes content, not the video stream itself. For video content, use `/cs:learn-yt` if the video is on YouTube.
