# Replication Run Comparison

Baseline: `replication/results_real_binanceusdm_large_76/summary.json`
Candidate: `replication/results_real_binanceusdm_large_76_llm/summary.json`

| metric               | baseline                        | candidate                       |      delta |
|:---------------------|:--------------------------------|:--------------------------------|-----------:|
| asset_count          | 69                              | 69                              |    0       |
| candle_count         | 656640                          | 656640                          |    0       |
| total_invocations    | 173                             | 173                             |    0       |
| trades_executed      | 139                             | 11                              | -128       |
| risk_approved        | 139                             | 11                              | -128       |
| risk_rejected        | 34                              | 162                             |  128       |
| agentic_friction_pct | 28.32369942196532               | 146.242774566474                |  117.919   |
| win_rate_pct         | 34.53237410071942               | 18.181818181818183              |  -16.3506  |
| profit_factor        | 0.5658311128336146              | 0.1076409316333886              |   -0.45819 |
| net_pnl_usd          | -34.725153204272694             | -7.981283722911384              |   26.7439  |
| execution_model      | ohlcv_intrabar_stop_take_profit | ohlcv_intrabar_stop_take_profit |            |

This comparison checks whether calibrated functional replication behavior remains stable across a larger public market universe. It does not empirically reproduce the original live dry-run without the authors' artefacts.
