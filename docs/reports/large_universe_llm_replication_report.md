# Large-Universe Deterministic and LLM Replication Report

Date: 2026-07-11

This report summarizes the local 76-symbol Binance USD-M functional replication run and the follow-on OpenRouter-backed LLM run. These runs use public reconstructed OHLCV/funding inputs and repository agents. They do not empirically reproduce the AGENTICAITA paper's original live dry-run because the original L2 snapshots, prompts, model completions, Risk Manager decisions, SQLite logs, funding cash flows, and production configuration history are unavailable.

## Inputs and Scope

The deterministic run fetched Binance USD-M one-minute public data for the paper window and selected 76 complete symbols for replication input.

| Field | Value |
| --- | --- |
| Exchange | `binanceusdm` |
| Profile | `large` |
| Requested symbol limit | `76` |
| Timeframe | `1m` |
| Window | `2026-04-06T00:00:00Z` to `2026-04-11T23:59:59Z` |
| Input rows | `656640` |
| Source symbols in replication input | `76` |
| Distinct normalized assets | `69` |
| Execution model | `ohlcv_intrabar_stop_take_profit` |

Primary local artefacts:

| Artefact | Path |
| --- | --- |
| Market database | `data/binanceusdm_ohlcv_large_76/market_data.sqlite` |
| Replication input CSV | `data/binanceusdm_ohlcv_large_76/replication_input_ohlcv.csv` |
| Selected symbols | `data/binanceusdm_ohlcv_large_76/complete_symbols_76.txt` |
| Coverage report | `data/binanceusdm_ohlcv_large_76/coverage_report.md` |
| Fetch manifest | `data/binanceusdm_ohlcv_large_76/manifest.json` |

The large local data artefacts should not be committed. They are retained locally so future runs can use `--skip-fetch` or call `replication/replicate.py` directly against the existing CSV.

## Deterministic Run

Command:

```bash
python scripts/run_real_data_replication.py \
  --profile large \
  --exchange binanceusdm \
  --symbol-limit 76 \
  --timeframe 1m \
  --start 2026-04-06T00:00:00Z \
  --end 2026-04-11T23:59:59Z
```

Outputs:

| Artefact | Path |
| --- | --- |
| Summary | `replication/results_real_binanceusdm_large_76/summary.json` |
| Trades | `replication/results_real_binanceusdm_large_76/trades.csv` |
| Used OHLCV | `replication/results_real_binanceusdm_large_76/ohlcv_used.csv` |
| Paper gap report | `replication/results_real_binanceusdm_large_76/paper_replication_gap_report.md` |

Deterministic summary:

| Metric | Value |
| --- | ---: |
| Total invocations | 173 |
| Analyst long | 72 |
| Analyst short | 86 |
| Analyst wait | 15 |
| Risk approved | 139 |
| Risk rejected | 34 |
| Trades executed | 139 |
| Wins | 48 |
| Losses | 91 |
| Net PnL USD | -34.725153204272694 |
| Gross profit USD | 45.2555967543605 |
| Gross loss USD abs | 79.9807499586332 |
| Win rate percent | 34.53237410071942 |
| Profit factor | 0.5658311128336146 |
| Agentic friction percent | 28.32369942196532 |

Paper comparison highlights:

| Item | Value |
| --- | ---: |
| Exact paper matches | 2 |
| Divergent paper metrics | 17 |
| Unavailable paper metrics | 0 |
| Replication total notional USD | 26132.00 |
| BTC price-only benchmark PnL USD | 1478.80 |
| Replication alpha versus BTC USD | -1513.52 |

The deterministic run matched the paper's Risk Manager approvals and executed trade count exactly, but diverged on signal mix, unique traded assets, win/loss counts, PnL, win rate, profit factor, and BTC benchmark alpha.

## LLM-Backed Run

The LLM-backed run reused the existing CSV and did not download market data.

Command:

```bash
python replication/replicate.py \
  --config replication/config.yaml \
  --input-csv data/binanceusdm_ohlcv_large_76/replication_input_ohlcv.csv \
  --out replication/results_real_binanceusdm_large_76_llm \
  --agents llm \
  --model qwen/qwen-2.5-7b-instruct \
  --audit-log replication/results_real_binanceusdm_large_76_llm/llm_audit.jsonl
```

Comparison commands:

```bash
python scripts/compare_replication_to_paper.py \
  --summary replication/results_real_binanceusdm_large_76_llm/summary.json \
  --trades replication/results_real_binanceusdm_large_76_llm/trades.csv \
  --ohlcv replication/results_real_binanceusdm_large_76_llm/ohlcv_used.csv \
  --out replication/results_real_binanceusdm_large_76_llm/paper_replication_gap_report.md

python scripts/compare_replication_runs.py \
  --baseline replication/results_real_binanceusdm_large_76/summary.json \
  --candidate replication/results_real_binanceusdm_large_76_llm/summary.json \
  --out docs/replication_deterministic_vs_llm_comparison.md
```

Outputs:

| Artefact | Path |
| --- | --- |
| Summary | `replication/results_real_binanceusdm_large_76_llm/summary.json` |
| Trades | `replication/results_real_binanceusdm_large_76_llm/trades.csv` |
| Used OHLCV | `replication/results_real_binanceusdm_large_76_llm/ohlcv_used.csv` |
| LLM audit log | `replication/results_real_binanceusdm_large_76_llm/llm_audit.jsonl` |
| Paper gap report | `replication/results_real_binanceusdm_large_76_llm/paper_replication_gap_report.md` |
| Deterministic vs LLM comparison | `docs/replication_deterministic_vs_llm_comparison.md` |

LLM summary:

| Metric | Value |
| --- | ---: |
| Total invocations | 173 |
| Analyst long | 16 |
| Analyst short | 66 |
| Analyst wait | 91 |
| Risk approved | 11 |
| Risk rejected | 162 |
| Trades executed | 11 |
| Wins | 2 |
| Losses | 9 |
| Net PnL USD | -7.981283722911384 |
| Gross profit USD | 0.9627434135197568 |
| Gross loss USD abs | 8.94402713643114 |
| Win rate percent | 18.181818181818183 |
| Profit factor | 0.1076409316333886 |
| Agentic friction percent | 146.242774566474 |

Paper comparison highlights:

| Item | Value |
| --- | ---: |
| Exact paper matches | 0 |
| Divergent paper metrics | 19 |
| Unavailable paper metrics | 0 |
| Replication total notional USD | 2068.00 |
| BTC price-only benchmark PnL USD | 117.03 |
| Replication alpha versus BTC USD | -125.01 |

The LLM-backed run was materially more conservative than the deterministic run. It produced the same 173 AZTE invocations, but only 11 approved/executed trades versus 139 in the deterministic run. The LLM run therefore had lower absolute net loss, but also much lower coverage, higher friction, lower win rate, and lower profit factor.

## LLM Usage and Cost

OpenRouter connectivity was confirmed before the full run with a lightweight smoke check. The full LLM run used `qwen/qwen-2.5-7b-instruct` through OpenRouter and wrote request/response audit rows to `replication/results_real_binanceusdm_large_76_llm/llm_audit.jsonl`.

Observed usage from the audit log:

| Metric | Value |
| --- | ---: |
| Audit rows | 184 |
| Prompt tokens | 126404 |
| Completion tokens | 30853 |
| Total tokens | 157257 |
| Reported OpenRouter cost USD | 0.0139344 |

The run emitted 17 warnings of the form `LLMAnalyst fallback to deterministic proxy: entry_price is required`. These warnings indicate that some Analyst responses were live LLM responses but did not satisfy the required schema for actionable entries, so the replication harness used its deterministic fallback for those Analyst decisions. The run still completed and produced a complete audit trail.

## Deterministic Versus LLM Comparison

| Metric | Deterministic | LLM | Delta |
| --- | ---: | ---: | ---: |
| Asset count | 69 | 69 | 0 |
| Candle count | 656640 | 656640 | 0 |
| Total invocations | 173 | 173 | 0 |
| Trades executed | 139 | 11 | -128 |
| Risk approved | 139 | 11 | -128 |
| Risk rejected | 34 | 162 | 128 |
| Agentic friction percent | 28.32369942196532 | 146.242774566474 | 117.91907514450868 |
| Win rate percent | 34.53237410071942 | 18.181818181818183 | -16.350555918901237 |
| Profit factor | 0.5658311128336146 | 0.1076409316333886 | -0.458190181200226 |
| Net PnL USD | -34.725153204272694 | -7.981283722911384 | 26.74386948136131 |

The LLM run confirms that model-backed decision logic can be exercised end-to-end on the public large-universe dataset, but it does not recreate the paper's LLM behavior. In this run, the live model's choices were far from the paper's reported long-biased signal mix and trade throughput.

## Interpretation

These runs support three conclusions:

1. The public-data functional replication path can process a 76-symbol Binance USD-M universe over the paper window and produce complete replication artefacts.
2. The deterministic proxy remains structurally calibrated for trade throughput, matching the paper's 139 executed trades, but its signal mix and outcome metrics remain divergent.
3. The OpenRouter-backed LLM path is operational and inexpensive for this workload, but the observed model behavior is substantially more conservative than both the deterministic proxy and the paper's reported Analyst/Risk Manager behavior.

The results should be read as functional replication evidence, not empirical validation of the original dry-run.
