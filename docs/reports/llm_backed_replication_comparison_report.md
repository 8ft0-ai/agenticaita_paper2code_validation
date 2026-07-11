# LLM-Backed Replication Comparison Report

Date: 2026-07-11

## Summary

This report documents the completed LLM-backed replication run for issue #122 and compares it with the deterministic 76-symbol fallback baseline. The run reused the existing Binance USD-M 76-symbol public-data input and did not download market data.

The LLM path completed end-to-end through OpenRouter using `qwen/qwen-2.5-7b-instruct`. This is not the paper's exact `qwen3.5:9b` remote Ollama model path, so the result is an LLM-backed behavioral comparison rather than a reproduction of the paper's original LLM decisions.

## Commands

The live-provider smoke check was run first to confirm OpenRouter connectivity:

```bash
cd replication
python llm_live_smoke.py \
  --out /var/folders/62/dljfp8k905lffg_vdv3whlyw0000gn/T/opencode/llm_connectivity_check \
  --model qwen/qwen-2.5-7b-instruct \
  --skip-without-key
cd ..
```

The LLM-backed replication then reused the existing CSV:

```bash
python replication/replicate.py \
  --config replication/config.yaml \
  --input-csv data/binanceusdm_ohlcv_large_76/replication_input_ohlcv.csv \
  --out replication/results_real_binanceusdm_large_76_llm \
  --agents llm \
  --model qwen/qwen-2.5-7b-instruct \
  --audit-log replication/results_real_binanceusdm_large_76_llm/llm_audit.jsonl
```

The paper gap and deterministic-vs-LLM comparison reports were generated with:

```bash
python scripts/compare_replication_to_paper.py \
  --summary replication/results_real_binanceusdm_large_76_llm/summary.json \
  --trades replication/results_real_binanceusdm_large_76_llm/trades.csv \
  --ohlcv replication/results_real_binanceusdm_large_76_llm/ohlcv_used.csv \
  --out replication/results_real_binanceusdm_large_76_llm/paper_replication_gap_report.md

python scripts/compare_replication_runs.py \
  --baseline replication/results_real_binanceusdm_large_76/summary.json \
  --candidate replication/results_real_binanceusdm_large_76_llm/summary.json \
  --out docs/reports/replication_deterministic_vs_llm_comparison.md
```

## Local Artefacts

| Artefact | Path |
| --- | --- |
| Deterministic summary | `replication/results_real_binanceusdm_large_76/summary.json` |
| Deterministic paper gap report | `replication/results_real_binanceusdm_large_76/paper_replication_gap_report.md` |
| LLM summary | `replication/results_real_binanceusdm_large_76_llm/summary.json` |
| LLM trades | `replication/results_real_binanceusdm_large_76_llm/trades.csv` |
| LLM pipeline log | `replication/results_real_binanceusdm_large_76_llm/pipeline_log.csv` |
| LLM audit log | `replication/results_real_binanceusdm_large_76_llm/llm_audit.jsonl` |
| LLM paper gap report | `replication/results_real_binanceusdm_large_76_llm/paper_replication_gap_report.md` |
| Comparison report | `docs/reports/replication_deterministic_vs_llm_comparison.md` |

Generated market data, replication output directories, and LLM audit logs remain local and should not be committed.

## OpenRouter Connectivity

The smoke check reported:

| Field | Value |
| --- | --- |
| Live provider available | `true` |
| Status | `live_provider_smoke` |
| Reason | `live provider used` |
| Model | `qwen/qwen-2.5-7b-instruct` |
| Provider path | OpenRouter |

The smoke audit contained live OpenRouter responses. The full run then completed with the same configured model.

## Deterministic Versus LLM Results

| Metric | Deterministic | LLM | Delta |
| --- | ---: | ---: | ---: |
| Asset count | 69 | 69 | 0 |
| Candle count | 656640 | 656640 | 0 |
| Total invocations | 173 | 173 | 0 |
| Analyst long | 72 | 16 | -56 |
| Analyst short | 86 | 66 | -20 |
| Analyst wait | 15 | 91 | 76 |
| Risk approved | 139 | 11 | -128 |
| Risk rejected | 19 | 71 | 52 |
| Risk not evaluated after Analyst wait | 15 | 91 | 76 |
| Trades executed | 139 | 11 | -128 |
| Wins | 48 | 2 | -46 |
| Losses | 91 | 9 | -82 |
| Net PnL USD | -34.725153204272694 | -7.981283722911384 | 26.74386948136131 |
| Win rate percent | 34.53237410071942 | 18.181818181818183 | -16.350555918901237 |
| Profit factor | 0.5658311128336146 | 0.1076409316333886 | -0.458190181200226 |
| Agentic friction percent | 19.653179190751445 | 93.64161849710983 | 73.98843930635839 |

The original generated summaries counted Analyst waits as Risk Manager rejections and then added those waits again when calculating friction. The corrected accounting treats the Risk Manager as not evaluated after a wait. Under that definition, the LLM-backed run still produced substantially more abstention and directional rejections than the deterministic baseline, resulting in only 11 executed trades versus 139. Contract failures and deterministic fallbacks mean this difference should not be attributed solely to model risk appetite.

## Paper Gap Results

The LLM paper gap report classified all 19 compared paper metrics as divergent.

| Metric | Paper | LLM Run | Classification |
| --- | ---: | ---: | --- |
| Total invocations | 157 | 173 | divergent |
| Analyst long | 142 | 16 | divergent |
| Analyst short | 2 | 66 | divergent |
| Analyst wait | 13 | 91 | divergent |
| Risk approved | 139 | 11 | divergent |
| Risk rejected | 5 | 71 | divergent |
| Trades executed | 139 | 11 | divergent |
| Unique traded assets | 76 | 10 | divergent |
| Wins | 72 | 2 | divergent |
| Losses | 67 | 9 | divergent |
| Net PnL USD | -15.07 | -7.981283722911384 | divergent |
| Win rate percent | 51.8 | 18.181818181818183 | divergent |
| Profit factor | 0.841 | 0.1076409316333886 | divergent |
| Agentic friction percent | 11.46 | 93.64161849710983 | divergent |
| BTC benchmark alpha USD | 3896.0 | -125.01 | divergent |

The LLM run did not recover the paper's long-heavy signal profile, trade throughput, win rate, profit factor, corrected friction, or positive benchmark alpha.

## LLM Usage and Fallbacks

Observed OpenRouter usage from the full-run audit log:

| Usage Metric | Value |
| --- | ---: |
| Audit rows | 184 |
| Prompt tokens | 126404 |
| Completion tokens | 30853 |
| Total tokens | 157257 |
| Reported OpenRouter cost USD | 0.0139344 |

The run emitted 17 warnings of the form `LLMAnalyst fallback to deterministic proxy: entry_price is required`. These warnings indicate that some live LLM Analyst responses did not satisfy the required actionable-entry schema. The harness used its deterministic fallback for those Analyst decisions and preserved the run-level audit trail.

## Interpretation

The LLM-backed path is operational and inexpensive for this workload, but it does not validate the paper's original LLM behavior. The model/provider combination used here is different from the paper's reported `qwen3.5:9b` remote Ollama path, and the original prompts, completions, model-serving conditions, Risk Manager decisions, market snapshots, and fallback traces are unavailable.

The result should therefore be read as a functional LLM-backed comparison over a public-data proxy dataset. It shows that the repository can run model-backed Analyst and Risk Manager agents end-to-end, while also showing that this available LLM path produces behavior that diverges substantially from the paper's reported agent behavior and outcomes.
