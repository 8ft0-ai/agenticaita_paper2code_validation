# Artifact Requirements

This page summarises which artefacts are needed for stronger reproduction claims.

## Artefacts available from public workflows

- OHLCV candles for supported public venues and symbols.
- Funding-rate history where the exchange exposes it through CCXT.
- Coverage reports, manifests, and SQLite candle stores generated locally.
- Functional replication outputs: `pipeline_log.csv`, `trades.csv`, `vol_history.csv`, `summary.json`, `replication_report.md`, and SQLite audit tables.

These files are generated artefacts and should remain outside git unless converted into a curated documentation summary.

## Artefacts required from the paper authors

- Original L2 order book snapshots.
- Original prompts, model calls, agent messages, and judge/risk-manager outputs.
- Original dry-run SQLite database and trade provenance.
- Original exchange fill, slippage, and execution assumptions.
- Any unreleased configuration needed to reproduce the exact five-day run.

Without these artefacts, the repository can provide static audit, functional replication, and comparable public-data reconstruction, but not an exact empirical reproduction of the original run.

## Repository policy

Use `docs/ci-operations/artifact_retention_policy.md` as the source of truth for what stays local, what may be committed, and what should be stored externally.
