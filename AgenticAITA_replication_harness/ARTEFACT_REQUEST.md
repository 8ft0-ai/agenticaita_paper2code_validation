# Artefacts required for empirical replication

To move from functional replication to empirical replication, request the following from the paper author:

1. SQLite database or exports of `trades`, `vol_history`, `pipeline_log`, and `ollama_calls`.
2. Exact asset universe, exchange/DEX identifier, and market symbols used from 2026-04-06 to 2026-04-11.
3. One-minute OHLCV, L2 order-book snapshots, funding rates, and BTC benchmark prices used by the system.
4. Exact prompts for Analyst, Risk Manager, and Executor, including JSON schema validators and retry logic.
5. Exact LLM model identifier, quantisation, temperature, context settings, and Ollama server logs.
6. IGP implementation details: mutex behaviour, cooldowns, discarded-trigger logging, and restart handling.
7. Dry-run exit/monitoring logic: how stop-loss/take-profit were simulated, whether intra-minute paths were considered, and whether any post-processing was applied.
8. Full configuration and container image hashes.
9. Evidence for zero human intervention: scheduler logs, deployment logs, and any manual restart records.

Without these artefacts, only internal consistency and functional reimplementation can be assessed.
