# 76-Symbol Fallback Replication Report

Date: 2026-07-11

## Summary

This report documents the completed 76-symbol Binance USD-M fallback replication for issue #120. The run used public one-minute OHLCV and available funding-history data as a feasible substitute for the paper's unavailable original Hyperliquid/live-market artefacts.

The run completed successfully, produced the expected local artefacts, and generated a paper gap report. It should be interpreted as a functional public-data replication, not an empirical reproduction of the AGENTICAITA paper's original dry-run.

## Command

The run was executed from the repository root:

```bash
python scripts/run_real_data_replication.py \
  --profile large \
  --exchange binanceusdm \
  --symbol-limit 76 \
  --timeframe 1m \
  --start 2026-04-06T00:00:00Z \
  --end 2026-04-11T23:59:59Z
```

## Data Source and Coverage

| Field | Value |
| --- | --- |
| Exchange | `binanceusdm` |
| Profile | `large` |
| Timeframe | `1m` |
| Window | `2026-04-06T00:00:00Z` to `2026-04-11T23:59:59Z` |
| Requested symbol limit | `76` |
| Selected source symbols | `76` |
| Distinct normalized assets | `69` |
| Replication input rows | `656640` |
| Expected candles per selected source symbol | `8640` |

Primary local artefacts:

| Artefact | Path |
| --- | --- |
| Coverage report | `data/binanceusdm_ohlcv_large_76/coverage_report.md` |
| Selected symbols | `data/binanceusdm_ohlcv_large_76/complete_symbols_76.txt` |
| Market database | `data/binanceusdm_ohlcv_large_76/market_data.sqlite` |
| Replication input CSV | `data/binanceusdm_ohlcv_large_76/replication_input_ohlcv.csv` |
| Fetch manifest | `data/binanceusdm_ohlcv_large_76/manifest.json` |

These data artefacts are intentionally local and should not be committed.

## Replication Outputs

| Artefact | Path |
| --- | --- |
| Summary | `replication/results_real_binanceusdm_large_76/summary.json` |
| Trades | `replication/results_real_binanceusdm_large_76/trades.csv` |
| Pipeline log | `replication/results_real_binanceusdm_large_76/pipeline_log.csv` |
| Replication report | `replication/results_real_binanceusdm_large_76/replication_report.md` |
| Paper gap report | `replication/results_real_binanceusdm_large_76/paper_replication_gap_report.md` |
| Used OHLCV | `replication/results_real_binanceusdm_large_76/ohlcv_used.csv` |

These generated run outputs are also intentionally local and should not be committed.

## Headline Metrics

| Metric | Value |
| --- | ---: |
| Total invocations | 173 |
| Analyst long | 72 |
| Analyst short | 86 |
| Analyst wait | 15 |
| Risk approved | 139 |
| Risk rejected | 19 |
| Risk not evaluated after Analyst wait | 15 |
| Stage accounting valid | `true` |
| Trades executed | 139 |
| Unique traded assets | 32 |
| Wins | 48 |
| Losses | 91 |
| Net PnL USD | -34.725153204272694 |
| Gross profit USD | 45.2555967543605 |
| Gross loss USD abs | 79.9807499586332 |
| Total notional USD | 26132.00 |
| Win rate percent | 34.53237410071942 |
| Profit factor | 0.5658311128336146 |
| Agentic friction percent | 19.653179190751445 |

The original generated summary counted the 15 Analyst waits as Risk Manager rejections and then added those waits again when calculating friction. The corrected accounting treats a wait as stopping before Risk Manager evaluation. The trade, PnL, win-rate, and profit-factor results are unchanged.

## Paper Gap Summary

The paper gap report classified the deterministic 76-symbol run as follows:

| Classification | Count |
| --- | ---: |
| Exact | 2 |
| Approximate | 0 |
| Divergent | 17 |
| Unavailable | 0 |

The exact matches were:

| Metric | Paper | Replication |
| --- | ---: | ---: |
| Risk Manager approvals | 139 | 139 |
| Executed dry-run trades | 139 | 139 |

All other compared paper aggregates were divergent, including total invocations, signal mix, unique traded assets, win/loss counts, PnL, win rate, profit factor, corrected friction, BTC benchmark PnL, and BTC benchmark alpha.

## BTC Price-Only Benchmark

The paper gap report computed a price-only BTC benchmark from the first and last BTC close in the supplied OHLCV artefact:

| Metric | Value |
| --- | ---: |
| BTC start close | 69102.9 |
| BTC end close | 73013.4 |
| BTC price return percent | 5.658952 |
| Replication total notional USD | 26132.00 |
| BTC benchmark PnL USD | 1478.80 |
| Replication alpha versus BTC USD | -1513.52 |

This benchmark is price-only arithmetic. It does not reproduce the paper's funding-adjusted perpetual-futures benchmark because the paper's original funding cash flows and sizing history are unavailable.

## Interpretation

The 76-symbol fallback run substantially expands the public functional-replication universe. It demonstrates that the repository can process 76 complete source symbols over the paper window and produce the required replication artefacts. The selected contracts normalised to 69 distinct input assets and only 32 assets traded, so this run does not reproduce the paper's 76 unique traded assets.

The run does not recover the paper's reported behavior or performance. It matched the paper's approval and execution counts, but it diverged on signal mix, unique traded assets, win/loss distribution, PnL, win rate, profit factor, corrected friction, and benchmark alpha.

## Limitations

This run uses Binance USD-M public data as a venue substitute. Public APIs and reconstructed OHLCV/funding data cannot recover the paper's original L2 order book snapshots, original LLM decisions, Risk Manager traces, author-side SQLite dry-run logs, funding-corrected benchmark records, or production configuration history.

The result should therefore be treated as a functional replication and gap analysis, not as independent validation of the paper's original live dry-run.
