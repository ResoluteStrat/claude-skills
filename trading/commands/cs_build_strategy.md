---
name: cs:build-strategy
description: Build or update a confidence-scored trading strategy document from all vault knowledge. Synthesizes concepts by tier, cites sources, and writes strategy_vN.md. Use weekly or after significant new knowledge is added.
---

# /cs:build-strategy

Full strategy synthesis from vault. Generates a versioned, confidence-scored strategy document.

## Pre-flight Gates

1. **Vault has sources** — refuse if `knowledge_vault.py --stats` shows 0 sources
2. **Instrument defined** — ask if not provided
3. **Timeframe defined** — ask if not provided
4. **Minimum source threshold** — warn (not refuse) if fewer than 5 sources ingested (LOW overall confidence)
5. **Forcing questions complete** — walk the 5 forcing questions from SKILL.md before synthesizing

## Forcing Questions (walk one at a time)

1. **Source count check**: "How many distinct sources are currently in the vault? Run `--stats` to verify."
   → Recommended answer: 10+ for a robust strategy

2. **Instrument focus**: "Which specific instrument is this strategy for? (ES, NQ, EURUSD, BTC, or 'multi')"
   → Recommended answer: single instrument for first strategy build

3. **Timeframe**: "What is your primary execution timeframe? And what is your HTF bias timeframe?"
   → Recommended answer: HTF = 4H or Daily for bias; LTF = 15m or 5m for entry

4. **Source diversity**: "Do your sources include at least: (a) one YouTube educator, (b) one Discord community, (c) one structured course?"
   → Recommended answer: yes to all three; diversity beats volume from one source

5. **Validation method**: "How will you validate this strategy before live capital? Paper trade? Replay? SIM?"
   → Recommended answer: minimum 50 replay trades before live

## Invocation

```bash
# Full synthesis
python trading/skills/trading-learning-agent/scripts/strategy_synthesizer.py \
  --synthesize \
  --instrument ES \
  --timeframe 15m \
  --output ~/.trading-vault/strategy_v{N}.md \
  --json

# Confidence overview only (no full document)
python trading/skills/trading-learning-agent/scripts/strategy_synthesizer.py \
  --confidence-report
```

## Output Summary

After synthesis, report to user:

```
✓ Strategy v4 generated: ~/.trading-vault/strategy_v4.md
  Instrument: ES | Timeframe: 15m
  Vault: 12 sources | 47 insights

  Concept distribution:
    VERY HIGH (7+ sources): 2 concepts
    HIGH (4-6 sources):     4 concepts
    MODERATE (2-3 sources): 3 concepts
    LOW (1 source):         2 concepts

  Changes from v3:
    ↑ order block: MODERATE → HIGH
    ↑ kill zone:   LOW → MODERATE
    NEW: breaker block (LOW — 1 source)

  ⚠ Low-confidence warning: 2 concepts are LOW — do not build hard rules
    around these until corroborated by additional independent sources.

  Disclaimer included. Review strategy_v4.md before trading.
```

## Hard Rules (enforced, not negotiable)

- Every concept in the document cites at least one `source_id` from the vault
- Confidence scores are never inflated — LOW is LOW regardless of how many times one educator repeated it
- The disclaimer block is always included and cannot be removed
- Output is always written as a new versioned file — previous versions are never overwritten
- The synthesizer does not fabricate entry rules, patterns, or risk parameters not present in vault insights

## After Strategy Is Generated

Recommend next steps:
1. Read `strategy_v{N}.md` from top to bottom
2. Identify any VERY HIGH / HIGH concept that lacks a corresponding `rules` insight in the vault — that's a gap
3. Add missing rules via `knowledge_vault.py --add-insight --category rules`
4. Re-run synthesis to incorporate the new rules
5. Paper trade the strategy for minimum 50 sessions before live capital
