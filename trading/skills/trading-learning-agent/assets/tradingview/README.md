# ProfitView DBO + Zone - TradingView scripts (experimental)

Files: `profitview_dbo_indicator.pine` (signals, zones, entry/stop/target lines, alerts) and
`profitview_dbo_strategy.pine` (same logic with orders for the Strategy Tester).

Install: TradingView > Pine Editor > paste the file > Save > Add to chart.
Set the chart timeframe to the ENTRY timeframe (5m for the taught method), Zone timeframe = 60.
Gold (XAUUSD / GC1!): max stop 4-6, buffer 0.2. NQ1!: max stop 30-45, buffer 1.
In the strategy, set Properties > Commission/Slippage to real costs.

Status: these scripts were written without a Pine compiler available. If TradingView shows a compile error,
paste the exact error text back. Backtests of this encoding (Python, gold and NQ futures, 60 days of 5m and
2 years of 1h) showed no statistically reliable positive expectancy after costs. Study tool, not a trading system.
