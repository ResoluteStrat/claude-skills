# Knowledge Entry Template

Use this template as a reference when manually adding insights to the vault via `knowledge_vault.py --add-insight`.

## CLI Invocation

```bash
python trading/skills/trading-learning-agent/scripts/knowledge_vault.py \
  --add-insight \
  --source-id <SOURCE_ID> \
  --category <CATEGORY> \
  --title "<TITLE>" \
  --content "<CONTENT>" \
  --tags "<TAG1>,<TAG2>,<TAG3>"
```

## Category Quick Reference

| Category | When to use |
|---|---|
| `concepts` | Defining what something IS — terminology, structure |
| `patterns` | Recurring price setups — what to look FOR |
| `rules` | Concrete if/then criteria — when to ENTER, EXIT, SIZE |
| `risk` | Loss limits, R-multiples, drawdown rules, position sizing |
| `psychology` | Mindset, emotional management, pre-trade routine |

## Tag Vocabulary (Canonical Forms)

Always use these exact strings to ensure consistent FTS search and confidence scoring:

```
order block
fair value gap
market structure
kill zone
liquidity
fibonacci
wyckoff
ict
smc
risk reward
higher timeframe
lower timeframe
session
bias
breaker
bms
swing high
swing low
premium
discount
bullish
bearish
continuation
reversal
consolidation
indices
forex
crypto
futures
ES
NQ
```

## Example Entries

### Concept Entry
```bash
python knowledge_vault.py --add-insight \
  --source-id 3 \
  --category concepts \
  --title "ICT Order Block Definition" \
  --content "An order block is the last up-candle (bullish OB) before a bearish impulse move, or the last down-candle (bearish OB) before a bullish impulse move. Price frequently returns to these zones to rebalance before continuing the impulse direction. Distinguished from random candles by the SUBSEQUENT impulse that displaces price away from that zone." \
  --tags "order block,ict,smart money,higher timeframe"
```

### Pattern Entry
```bash
python knowledge_vault.py --add-insight \
  --source-id 5 \
  --category patterns \
  --title "FVG Fill into Order Block Confluence" \
  --content "When price creates a Fair Value Gap (imbalance) directly above or below an identified Order Block, the confluence of the two PD arrays creates a higher-probability reversal zone. Wait for LTF structure break within the OB + FVG confluence zone as confirmation before entry." \
  --tags "fair value gap,order block,confluence,reversal,lower timeframe"
```

### Rule Entry
```bash
python knowledge_vault.py --add-insight \
  --source-id 2 \
  --category rules \
  --title "Kill Zone Only Entry Rule" \
  --content "Only execute entries during ICT Kill Zones: London Open (02:00-05:00 EST), New York Open (07:00-10:00 EST), London Close (10:00-12:00 EST). No entries outside these windows regardless of setup quality. Kill zones align with institutional order flow participation." \
  --tags "kill zone,ict,session,entry,london,new york"
```

### Risk Entry
```bash
python knowledge_vault.py --add-insight \
  --source-id 1 \
  --category risk \
  --title "Maximum Daily Loss Rule" \
  --content "Hard stop at 2% account loss per day. When daily drawdown reaches 2%, close all positions immediately and do not trade for the remainder of the session. No exceptions. This rule exists because revenge trading after losses creates compounding drawdown." \
  --tags "risk,drawdown,position sizing,discipline"
```

### Psychology Entry
```bash
python knowledge_vault.py --add-insight \
  --source-id 7 \
  --category psychology \
  --title "Pre-Trade Checklist Discipline" \
  --content "Before any entry: (1) Confirm HTF bias is clear, (2) Identify the PD array you are targeting, (3) Define the entry trigger on LTF, (4) Set the stop loss BEFORE entry, (5) Calculate position size for defined stop. If any of these five steps cannot be completed, there is no trade. Trade the plan, not the moment." \
  --tags "psychology,discipline,checklist,entry,risk"
```

## Looking Up Source IDs

```bash
# List all sources to find the source_id you want to cite
python knowledge_vault.py --list-sources
```

Output shows:
```
ID  | Type     | Title                          | Ingested
----|----------|--------------------------------|-------------------
1   | youtube  | ICT 2022 Mentorship Episode 1  | 2025-11-15T14:30Z
2   | youtube  | ICT Order Blocks Explained     | 2025-11-15T14:45Z
3   | discord  | #setups general                | 2025-11-15T15:00Z
```
