# Strategy Synthesis Framework

## Purpose
Defines how the Trading Learning Agent converts accumulated vault knowledge into a confidence-scored, actionable trading strategy document. Synthesis is the output phase — the moment raw learning becomes usable edge.

## Sources
1. Mark Douglas, *Trading in the Zone* — edge is probabilistic, not predictive
2. Van K. Tharp, *Trade Your Way to Financial Freedom* — expectancy formula, position sizing system
3. ICT (Michael Huddleston) public lectures — kill zones, HTF bias, LTF entry model
4. Richard Wyckoff — phase reading, composite operator intent
5. Bessemer Venture Partners sizing framework — confidence tiers as capital allocation signal (adapted for position sizing)
6. Richard Feynman — "If you can't explain it simply, you don't understand it" (strategy clarity standard)
7. Tom Hougaard, *Best Loser Wins* — rules must survive emotional state; write them in advance

## Synthesis Pipeline

### Step 1 — Concept Scanning (`_scan_vault_sources`)
For each canonical concept in `CORE_CONCEPTS`, the synthesizer:
1. Scans all source `.md` files for keyword and alias matches
2. Queries `insights` table for tagged and categorized references
3. Records which **distinct** `source_id` values mention the concept

Critical invariant: the same concept mentioned 10 times in one video counts as **1** source, not 10. Confidence is earned through independent corroboration, not repetition within a single voice.

### Step 2 — Confidence Tier Assignment
```
7+ distinct sources  → VERY HIGH  — load-bearing for strategy
4–6 distinct sources → HIGH       — include with defined rules
2–3 distinct sources → MODERATE   — include with caveats
1 distinct source    → LOW        — file, do not build rules around yet
```

### Step 3 — Strategy Document Structure

The output is a markdown file at `~/.trading-vault/strategy_vN.md` (auto-incremented version number). Structure:

```markdown
# Trading Strategy v{N} — {INSTRUMENT} {TIMEFRAME}
Generated: {datetime}
Vault sources: {count} | Total insights: {count}

---

## VERY HIGH Confidence Concepts
> Corroborated by 7+ independent sources. Consider load-bearing.

### {Concept Name} [VERY HIGH — {N} sources]
**Supporting Insights:**
- [{insight_title}] — {content_excerpt} *(Source: {source_title})*

---

## HIGH Confidence Concepts
...

## MODERATE Confidence Concepts
...

## LOW Confidence Concepts
...

---

## Disclaimer
> This document is synthesized from educational sources and market observations.
> It is NOT financial advice. All trading involves risk of loss. Past patterns
> do not guarantee future results. Trade only what you understand and can afford to lose.
```

### Step 4 — Confidence Report (separate view)

The `--confidence-report` flag produces a table view without the full insight detail — useful for quick morning review:

```
Concept                    | Confidence  | Sources | Mentions
---------------------------|-------------|---------|----------
order block                | VERY HIGH   |    8    |   23
fair value gap             | VERY HIGH   |    7    |   19
liquidity                  | HIGH        |    5    |   14
kill zone                  | HIGH        |    4    |   11
market structure           | MODERATE    |    3    |    8
wyckoff                    | LOW         |    1    |    2
```

## Concept Normalization

The synthesizer maps aliases to canonical forms before scanning. This prevents the same concept from appearing as low-confidence because users and educators use different abbreviations:

| Alias | Canonical |
|---|---|
| ob, OB, order_block | order block |
| fvg, FVG, fair_value_gap, imbalance | fair value gap |
| bos, BOS, break of structure | structure break |
| choch, CHoCH, change of character | character change |
| htf, HTF | higher timeframe |
| ltf, LTF | lower timeframe |
| r:r, rr, risk/reward | risk reward |
| smc, SMC, smart_money | smart money |
| liq, LIQ | liquidity |
| pd, PD array | premium discount |
| msb, MSB | structure break |
| poi, POI, point of interest | point of interest |

## Instrument and Timeframe Scoping

The synthesizer accepts optional `--instrument` and `--timeframe` filters. When provided:
- Content scan prioritizes source files whose title or content mentions the instrument (e.g., "ES", "NQ", "futures", "indices")
- Timeframe filters prioritize content mentioning the timeframe (e.g., "15m", "1H", "daily")
- Unscoped sources are still included but labeled as `[general]`

This allows generating a focused "ES 15m strategy" from a vault that also contains FX and crypto content.

## Expectancy Integration (Tharp-aligned)

When the vault contains enough `rules` and `risk` category insights with numerical data, the synthesizer surfaces an expectancy estimate:

```
Expectancy = (Win Rate × Avg Win) − (Loss Rate × Avg Loss)

Example from vault insights:
  Win rate target: 40% (from risk insights)
  Avg win: 3R (from rules insights)
  Avg loss: 1R (defined)
  Expectancy = (0.40 × 3) − (0.60 × 1) = 0.60R per trade
```

If numerical data is absent from insights, this section is omitted — never fabricated.

## Hard Rules for Synthesis

1. **Never invent** — every strategy element must trace to at least one `source_id` in the vault
2. **Never inflate confidence** — if a concept appears in 3 sources, it is MODERATE, never HIGH
3. **Always version** — each synthesis run increments the version number; old strategies are not overwritten
4. **Always disclaim** — the disclaimer block is mandatory and cannot be removed via flags
5. **Low confidence concepts are still included** — they belong in the strategy document with their LOW label; silence is not transparency

## Strategy Evolution Cadence

Recommended synthesis schedule:
- **End of each learning session** — run `--digest-day` after significant new content ingest
- **Weekly** — run `--build-strategy` to get an updated confidence landscape
- **After 5+ new sources added** — re-synthesize to see if any concepts crossed a confidence tier

Douglas's insight: the edge must be defined before emotional pressure hits. Writing the strategy in advance, while calm, is the execution discipline. The synthesis script enforces this by making the rules explicit and versioned.
