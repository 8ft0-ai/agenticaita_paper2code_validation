# AGENTICAITA functional replication run

Data source: `deterministic_synthetic`

This run executes the paper's published architecture in dry-run form: AZTE trigger, CBD score, sequential analyst/risk/executor pipeline, deterministic risk gates, IGP cooldowns, SQLite audit tables, and transaction-cost sensitivity.

It is not an empirical replication unless supplied with the author's raw market data, order-book/funding snapshots, exact prompts, LLM outputs, and SQLite logs.

## Summary

```json
{
  "total_invocations": 44,
  "analyst_long": 21,
  "analyst_short": 23,
  "analyst_wait": 0,
  "risk_approved": 43,
  "risk_rejected": 1,
  "trades_executed": 43,
  "wins": 21,
  "losses": 22,
  "net_pnl_usd": -3.2254029540730307,
  "gross_profit_usd": 20.32288353584378,
  "gross_loss_usd_abs": 23.548286489916812,
  "win_rate_pct": 48.83720930232558,
  "profit_factor": 0.8630302482750019,
  "agentic_friction_pct": 2.272727272727273,
  "exact_binomial_p_one_sided": 0.619604178719328,
  "normal_approx_p_one_sided": 0.5606031410203511
}
```

## Transaction-cost sensitivity

| scenario                    |   round_trip_rate |   total_cost_usd |   adjusted_net_pnl_usd |
|:----------------------------|------------------:|-----------------:|-----------------------:|
| zero_cost                   |            0      |           0      |                -3.2254 |
| conservative_maker_only     |            0.0004 |           3.2336 |                -6.459  |
| realistic_taker_plus_spread |            0.001  |           8.084  |               -11.3094 |
| adverse_illiquid_long_tail  |            0.002  |          16.168  |               -19.3934 |