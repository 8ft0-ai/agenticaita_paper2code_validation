# Replication Run Comparison

Baseline: `replication/results_real_binanceusdm_large_76/summary.json`
Candidate: `replication/results_real_binanceusdm_large_76_llm/summary.json`

| metric | baseline | candidate | delta |
| --- | ---: | ---: | ---: |
| asset_count | 69 | 69 | 0 |
| candle_count | 656640 | 656640 | 0 |
| total_invocations | 173 | 173 | 0 |
| trades_executed | 139 | 11 | -128 |
| risk_approved | 139 | 11 | -128 |
| risk_rejected | 34 | 162 | 128 |
| agentic_friction_pct | 28.32369942196532 | 146.242774566474 | 117.91907514450868 |
| win_rate_pct | 34.53237410071942 | 18.181818181818183 | -16.350555918901237 |
| profit_factor | 0.5658311128336146 | 0.1076409316333886 | -0.458190181200226 |
| net_pnl_usd | -34.725153204272694 | -7.981283722911384 | 26.74386948136131 |
| execution_model | ohlcv_intrabar_stop_take_profit | ohlcv_intrabar_stop_take_profit |  |

This comparison checks whether calibrated functional replication behavior remains stable across a larger public market universe when the deterministic proxy is replaced by OpenRouter-backed LLM agents. It does not empirically reproduce the original live dry-run without the authors' artefacts, and the LLM run used `qwen/qwen-2.5-7b-instruct` through OpenRouter rather than the paper's exact `qwen3.5:9b` remote Ollama path.
