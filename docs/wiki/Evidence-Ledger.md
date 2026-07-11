# Evidence Ledger

This page records the evidence levels used by the repository when assessing AGENTICAITA claims.

| Evidence level | Meaning | Repository location |
| --- | --- | --- |
| Static audit | Reported quantities are checked for internal consistency. | `validation/` |
| Functional replication | The published architecture is approximated and executed in an auditable dry-run harness. | `replication/` |
| Empirical public-data reconstruction | Public market data is fetched and used for comparable market-condition checks. | `scripts/fetch_hyperliquid_ohlcv.py`, `scripts/run_real_data_replication.py` |
| Author artefacts required | A claim depends on unreleased prompts, LLM calls, order books, trade logs, or SQLite records. | Tracked in validation reports and issue discussions. |

## Current public-data limitation

The documented Hyperliquid paper-window attempt returned funding rows for the requested symbols but no OHLCV candles. The repository therefore uses Binance USD-M as a CCXT-compatible public perpetual-futures fallback for comparable market-condition checks. The fallback does not reproduce the paper's exact venue, liquidity, order-book state, or original dry-run decisions.

## Material benchmark finding

The paper describes BTC losing approximately 15% over 6–11 April 2026. The complete Binance USD-M reconstruction records BTC rising from 69,102.9 to 73,013.4, or approximately +5.659%, and contemporaneous public reports support an upward move across those dates.

This claim is classified as **divergent and unresolved**, not as a normal venue-substitution variance. The full calculation, alternative interpretations, independent directional cross-check, and author clarification request are recorded in [`btc_benchmark_window_contradiction.md`](../investigations/btc_benchmark_window_contradiction.md).

## Evidence handling rule

Do not upgrade a result from functional replication to empirical replication unless the run uses documented market data, passes quality checks, and clearly states its remaining limitations.
