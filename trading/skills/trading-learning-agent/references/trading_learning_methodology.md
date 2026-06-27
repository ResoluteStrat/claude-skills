# Trading Learning Methodology

## Purpose
This reference defines how the Trading Learning Agent acquires, validates, and retains trading knowledge from heterogeneous sources (video, chat, structured courses). Every design decision traces back to one principle: **verbatim recall over lossy summarization**.

## Sources
1. Mark Douglas, *Trading in the Zone* (2000) — probabilistic mindset, edge definition
2. Michael Huddleston (ICT), YouTube public lectures — order blocks, fair value gaps, kill zones, liquidity
3. Richard Wyckoff, *Studies in Tape Reading* (1910) — accumulation/distribution cycles, composite operator
4. Van K. Tharp, *Trade Your Way to Financial Freedom* (1999) — position sizing, expectancy, R-multiples
5. Brett Steenbarger, *The Psychology of Trading* (2002) — performance psychology, journaling
6. Tom Hougaard, *Best Loser Wins* (2022) — emotional counterintuition in execution
7. NN/g Research on information retention — spaced repetition, chunked review

## Core Methodology

### Phase 1 — Ingest
Each ingestor extracts content from one source type and writes two artifacts:
- **Verbatim source file** (`~/.trading-vault/sources/<type>/<id>.md`) — exact transcription or content, never paraphrased
- **SQLite row** in `sources` table — metadata pointer to the file

Ingestors never interpret. They capture exactly what was said, typed, or written.

### Phase 2 — Vault (knowledge_vault.py)
The vault layer sits between raw sources and the strategy synthesizer. It stores analyst-extracted insights — manually or semi-automatically added observations that cite a `source_id`. Insight categories:

| Category | What belongs here |
|---|---|
| `concepts` | Definitions — what is an order block, what is a kill zone |
| `patterns` | Recurring price structures — FVG fill, liquidity sweep then reversal |
| `rules` | Entry/exit criteria — only trade ICT kill zones, minimum 1:3 RR |
| `risk` | Position sizing rules, max daily loss, drawdown thresholds |
| `psychology` | Mindset notes — remove emotion from entries, trade the plan |

### Phase 3 — Synthesize
The synthesizer scans vault sources and counts **independent source corroboration** for each concept. Confidence is earned by repetition across multiple independent educators, not by one teacher saying something many times.

```
Confidence = f(distinct_source_count)
1 source   → LOW
2-3        → MODERATE
4-6        → HIGH
7+         → VERY HIGH
```

This mirrors how scientific confidence is established: independent replication, not volume of repetition from a single voice.

## Verbatim-First Discipline

### Why verbatim?
Market structure concepts are precise. "Order block" in ICT means a specific candle (last up-candle before a bearish impulse, or last down-candle before a bullish impulse). Paraphrasing introduces drift. When you search the vault three months later, you need the exact framing the educator used, not a lossy summary that lost the edge condition.

### Verbatim does NOT mean no filtering
Discord harvesting applies a keyword filter to skip off-topic banter. This is relevance gating, not paraphrasing. Messages that pass the filter are stored verbatim.

### When to add insights manually
After reviewing ingested content, the user (or agent) adds structured insights via `knowledge_vault.py --add-insight`. These are the analyst's interpretation layer — but they always cite a `source_id` so the original verbatim source is always reachable.

## Confidence Scoring Philosophy (Douglas-aligned)

Mark Douglas establishes that a trader's edge is a probability, not a certainty. The confidence score in this system is analogous: it expresses how many independent data points corroborate a concept, not how "true" the concept is.

- **VERY HIGH (7+ sources)**: Concept appears across major YouTube educators, at least one Discord community, and at least one structured course. Consider it load-bearing for strategy.
- **HIGH (4-6)**: Cross-validated across multiple educators. Solid enough to include in strategy with defined rules.
- **MODERATE (2-3)**: Seen multiple times but not widely corroborated. Include with caveats.
- **LOW (1)**: Single source. File it, but do not build rules around it without further validation.

## Spaced Review Recommendation

Van Tharp and Steenbarger both emphasize journaling and review as performance multipliers. The agent's `--digest-day` command operationalizes this: run it at session end to consolidate the day's learning before it fades from working memory.

## Anti-Patterns to Avoid

1. **Summarizing transcripts** — destroys nuance and removes searchability of exact phrases
2. **Fabricating source citations** — every insight must trace to a real `source_id` in the vault
3. **Treating HIGH confidence as certainty** — all concepts are probabilistic edges, not facts
4. **Skipping the verbatim file** — the insight layer is useful; the verbatim source is irreplaceable
5. **Ingesting without tagging** — untagged insights are unsearchable; always provide `--tags`
