# Replication matrix

| Paper claim family | Current status | What this harness does | What is still needed |
|---|---:|---|---|
| AZTE trigger equations | Functionally reproduced | Implements rolling r_t, z_t, and `z >= 2 or r >= 0.003` | Exact author code and convention for including/excluding current observation in rolling baseline |
| SDP multi-agent pipeline | Functionally approximated | Uses typed Analyst/Risk/Executor contracts and sequential execution | Exact prompts, model, sampling parameters, raw LLM outputs, failure handling |
| Risk Manager hard gates | Functionally reproduced | Enforces confidence, stop-loss, and size gates deterministically | Author's contextual LLM risk-manager decisions |
| IGP serialisation | Functionally approximated | Implements global and per-asset cooldown admission | Author's exact mutex/cooldown implementation and concurrent trigger logs |
| CBD formula | Functionally reproduced | Implements z saturation, correlation break, omega score | Raw per-asset price windows and correlation values used by authors |
| 157 invocations / 139 trades | Not independently replicated | Produces comparable invocation/trade counts on supplied data | Author's full market universe, timestamps, market data, logs |
| 11.5% agentic friction | Audited, not empirically replicated | Computes friction from generated pipeline logs | Author pipeline logs with wait/reject records |
| PnL / win rate / profit factor | Audited, not empirically replicated | Computes metrics from generated trades | Author trades table and exit logic/fill data |
| BTC benchmark alpha | Audited with caveats | Can compute benchmark if supplied benchmark prices and funding series | Exact benchmark capital convention, BTC price path, funding cash flows |
| Transaction-cost sensitivity | Reproduced at table-arithmetic level | Computes notional-rate cost scenarios | Live fills, spreads, volumes, impact calibration |
| Zero human intervention | Unsupported | None | Deployment logs, scheduler logs, operational audit trail |
