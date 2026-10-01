# ProfitView DBO + Zone - backtest results (2026-10-01)

Script: `scripts/backtest_profitview.py`. Data: Yahoo continuous futures (GC=F gold, NQ=F), 60 days of 5m
(2026-07-23 to 2026-10-01) and 2 years of 1h (2024-05-09 to 2026-10-01). Costs deducted (gold 0.2-0.4, NQ 0.5-1.0 per round trip).
Stop assumed hit first if stop and target share a bar. Random-entry benchmark = same stop/target/costs at random times.

| Dataset | Variant | Trades | Best exit | Avg R | Verdict |
|---|---|---|---|---|---|
| Gold 5m | DBO only | 572-842 | fixed 3R | -0.11 to -0.23 | loses |
| Gold 5m | DBO + 1h zone | 38-50 | fixed 3R | -0.11 to 0.0 | break-even at best, n too small |
| Gold 1h (2y) | DBO only | 744 | fixed 3R | +0.07 (95% CI -0.06..+0.21) | not distinguishable from zero |
| Gold 1h (2y) | DBO + 4h zone | 42 | fixed 3R | +0.07 (CI -0.43..+0.65) | n too small |
| NQ 5m | DBO only | 914-1079 | fixed 2-3R | -0.16 to -0.19 | loses |
| NQ 5m | DBO + 1h zone | 62-76 | fixed 2R | -0.25 to -0.37 | loses |
| NQ 1h (2y) | DBO only | 828 | fixed 3R | -0.15 | loses |

Conclusion: no reliable positive expectancy in the mechanical encoding. The pattern beats random entries slightly
(random-entry baseline also negative from costs) but not enough to cover costs. Zone filter leaves too few trades to judge.
Not captured: instructor's discretionary storyline/direction filter, visual judgement, session timing, news, live execution.
