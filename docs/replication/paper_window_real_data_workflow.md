# Paper-Window Real-Data Workflow

The manual `Paper Window Real Data Replication` workflow runs the closest available public-data reconstruction of the AGENTICAITA paper window.

Defaults:

- window: `2026-04-06T00:00:00Z` through `2026-04-11T23:59:59Z`;
- timeframe: `1m`;
- profile: `baseline-15`;
- baseline symbol count: `15`.

Use `closest` mode for the standard reconstruction. It attempts Hyperliquid first because that is closest to the paper venue. If Hyperliquid cannot produce complete exportable OHLCV coverage for the paper window, the workflow falls back to Binance USD-M perpetual futures for the same baseline asset universe.

The workflow runs `scripts/run_real_data_replication.py`, `scripts/check_replication_quality.py`, run-manifest generation, result indexing, dashboard rendering, a GitHub Actions summary, and a compact artefact upload.

Uploaded artefacts include coverage reports, complete-symbol lists, run manifests, quality reports, replication summaries, result indexes, dashboard output, and logs. Raw SQLite databases and raw per-symbol OHLCV CSV directories are not uploaded by default. Set `upload_replication_input` to `true` only when the exported replication input CSV is needed for review or later promotion.

This is a public-market comparable reconstruction, not an exact recovery of the original order books, prompts, LLM calls, dry-run SQLite logs, or execution assumptions.
