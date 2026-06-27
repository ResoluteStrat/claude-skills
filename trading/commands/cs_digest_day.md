---
name: cs:digest-day
description: Synthesize end-of-day learning into a structured digest showing what was ingested, which confidence tiers changed, new insights added, and tomorrow's learning priorities. Run at end of each trading study session.
---

# /cs:digest-day

End-of-session consolidation. Produces a daily digest from `strategy_synthesizer.py` + vault stats.

## Pre-flight Gates

1. **Vault exists** — verify `~/.trading-vault/vault.db` exists
2. **At least 1 source ingested today** — check `ingested_at` >= today 00:00 UTC
3. **Instrument defined** — ask if not already known (needed for scoped confidence report)

## Invocation

```bash
# Step 1: Vault stats for today
python trading/skills/trading-learning-agent/scripts/knowledge_vault.py \
  --stats --json

# Step 2: Confidence tier overview
python trading/skills/trading-learning-agent/scripts/strategy_synthesizer.py \
  --confidence-report --json

# Step 3: Export insights to markdown (for human review)
python trading/skills/trading-learning-agent/scripts/knowledge_vault.py \
  --export-insights
```

## Digest Sections

### 1. Today's Ingested Sources
List all sources with `ingested_at` >= today. Show type, title, content volume.

### 2. Confidence Changes
Compare current confidence counts to the previous digest (or baseline). Highlight any concept that crossed a tier boundary today.

### 3. New Insights Added
List all insights with `created_at` >= today, grouped by category.

### 4. Current Strategy Snapshot
Show all concepts grouped by confidence tier. Bold any that changed today.

### 5. Tomorrow's Learning Priorities
Identify the 3 lowest-confidence concepts that are referenced in current strategy rules. These are the gaps to close first.

## Example Invocation

User says: "Let's digest today's learning"

Agent response:
```
Running end-of-day digest for 2025-11-15...

Today's sources: 3 ingested
  - ICT 2022 Mentorship Ep.14 (YouTube, 1h 23m)
  - #setups-general Nov 15 (Discord, 234 messages)
  - SMC Mastery Module 3 (Teachable, 4,821 words)

Confidence changes:
  order block: MODERATE → HIGH (new source: ICT Ep.14)
  kill zone:   LOW → MODERATE (new source: SMC Module 3)

New insights: 5 added
  Concepts: 2  |  Patterns: 1  |  Rules: 1  |  Psychology: 0  |  Risk: 0

Current strategy snapshot:
  VERY HIGH: fair value gap (8), market structure (7)
  HIGH: order block (4) ↑, liquidity (5), kill zone (4) ↑, risk reward (4)
  MODERATE: fibonacci (3), wyckoff (3)
  LOW: breaker block (1), mitigation block (1)

Tomorrow's priorities:
  1. Breaker block — only 1 source; find ICT or SMC educator content
  2. Mitigation block — only 1 source; OB invalidation logic needs corroboration
  3. Psychology — 0 insights in this category; critical gap

Digest complete. Last full synthesis: strategy_v3.md (2025-11-14)
Run /cs:build-strategy to generate updated strategy_v4.md
```
