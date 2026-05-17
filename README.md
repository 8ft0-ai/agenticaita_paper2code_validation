# agenticaita_paper2code_validation
agenticaita_paper2code_validation

## Validation And Replication Scope

This repository contains two complementary Paper2Code validation paths:

| Directory | Purpose | Scenario | Main outputs |
| --- | --- | --- | --- |
| `validation/` | Checks whether the paper's reported quantities are internally consistent and flags claims that need missing artefacts. | Static claim audit / Paper2Code validation. | `validation_report.md`, JSON/CSV validation results, optional real-data validation reports. |
| `replication/` | Runs an executable dry-run approximation of the published architecture. | Functional simulation / architecture replication. | SQLite audit DB, `pipeline_log.csv`, `trades.csv`, `vol_history.csv`, summary JSON, replication report. |

`validation/` does not recreate the live trading system. It validates reproducible arithmetic and statistical claims from reported quantities such as invocations, trades, assets, PnL, cost scenarios, binomial checks, and CBD properties, while marking raw-data-dependent claims as unsupported.

`replication/` does not prove the original five-day live dry-run results. It implements the published architecture components, including AZTE, CBD, a sequential Analyst -> Risk Manager -> Executor pipeline, risk hard gates, IGP cooldowns, audit artefacts, and cost sensitivity, so new runs can produce comparable artefacts.

Both paths touch the same paper concepts, but they answer different questions:

| Question | Directory |
| --- | --- |
| Are the paper's reported numbers internally consistent, and which claims are unsupported without missing artefacts? | `validation/` |
| Can we build and run an auditable dry-run system matching the published architecture closely enough to generate comparable artefacts? | `replication/` |

## Hyperliquid OHLCV Downloader

This workflow reconstructs public market conditions for the AGENTICAITA paper window. It does not reproduce the original agent decisions or dry-run audit log unless the authors' original artefacts are provided.

## Historical Real-Data Validation Plan

The issue #7 tracking plan is now represented by the repository workflow:

1. Fetch Hyperliquid one-minute perpetual OHLCV and available funding history for `2026-04-06T00:00:00Z` through `2026-04-11T23:59:59Z` with `scripts/fetch_hyperliquid_ohlcv.py`.
2. Review generated `coverage_report.md` / `coverage_report.json` for symbol coverage, gaps, duplicates, funding availability, and per-symbol failures.
3. Compute deterministic AZTE/CBD reconstruction metrics from the downloaded SQLite store with `scripts/compute_azte_cbd_metrics.py`.
4. Run `validation/validate_claims.py --market-db ...` to produce real-data validation reports.

This plan can validate public market-data-dependent checks only. It cannot recover the paper's original L2 order book snapshots, LLM decisions, prompts, risk-manager approvals, SQLite logs, or exact dry-run trade path without those original artifacts.

Install dependencies:

```bash
pip install -r requirements.txt
```

Smoke-test a small active perpetual/swap subset:

```bash
python scripts/fetch_hyperliquid_ohlcv.py --symbol-limit 3
```

Download all active Hyperliquid perpetual/swap symbols for the AGENTICAITA reconstruction window:

```bash
python scripts/fetch_hyperliquid_ohlcv.py
```

The default window is `2026-04-06T00:00:00Z` through `2026-04-11T23:59:59Z`, using `ccxt.hyperliquid` and `1m` candles. Raw per-symbol OHLCV CSV files, `manifest.json`, `market_data.sqlite`, and coverage reports are written under `data/hyperliquid_ohlcv/`, which is intentionally ignored by git. Funding-rate history is requested with CCXT `fetch_funding_rate_history` when the exchange exposes it; unavailable or empty funding history is recorded as metadata and does not block OHLCV reconstruction.

Expected runtime and storage depend on exchange rate limits and active symbol count. A three-symbol smoke run should complete in minutes and use a small local SQLite/CSV footprint. An all-symbol one-minute download for the full five-day window can take tens of minutes or longer and may require hundreds of MB after CSV, SQLite, manifest, and report outputs are included.

The SQLite database is created automatically. Its validation-facing schema is:

| Table | Purpose |
| --- | --- |
| `symbols` | Exchange symbol catalog with `exchange_id`, `symbol`, `market_type`, active status, and first/last seen timestamps. |
| `candles` | OHLCV candles keyed by `exchange_id`, `symbol`, `timeframe`, and `timestamp_ms`, plus UTC timestamp, OHLCV fields, and retrieval time. |
| `funding_rates` | Funding-rate storage keyed by `exchange_id`, `symbol`, and `timestamp_ms` for validation/backtest adapters that need funding context. |
| `fetch_metadata` | Per-symbol retrieval status with requested window, data kind (`ohlcv` or `funding`), CCXT method, row count, error text, CSV path, and retrieval time. |

After each run, `coverage_report.md` and `coverage_report.json` summarize candle counts, expected counts, missing interval samples, duplicate timestamps, unavailable symbols, funding availability, and symbols with incomplete data. Price-only benchmarks only require complete OHLCV; funding-adjusted benchmarks should be treated as unsupported or incomplete for symbols without stored `funding_rates` rows.

Useful options:

```bash
python scripts/fetch_hyperliquid_ohlcv.py --symbols BTC/USDC:USDC,ETH/USDC:USDC --out data/hyperliquid_ohlcv_smoke
python scripts/fetch_hyperliquid_ohlcv.py --db data/hyperliquid_ohlcv/market_data.sqlite
python scripts/fetch_hyperliquid_ohlcv.py --max-retries 5 --retry-sleep 3 --limit 1000
python scripts/fetch_hyperliquid_ohlcv.py --funding-limit 1000
```

Failures are recorded per symbol in `manifest.json`; one symbol failure does not abort the rest of the run.

If Hyperliquid historical coverage is incomplete, rerun with explicit subsets to isolate missing markets, then use CCXT-compatible fallback venues only for comparable public market-condition checks:

```bash
python scripts/fetch_hyperliquid_ohlcv.py --symbols BTC/USDC:USDC,ETH/USDC:USDC
python scripts/fetch_hyperliquid_ohlcv.py --exchange binanceusdm --symbols BTC/USDT:USDT,ETH/USDT:USDT --out data/binanceusdm_ohlcv
```

Fallback exchange data is not a replacement for the paper's exact Hyperliquid session. It can support sensitivity checks against public OHLCV/funding conditions, but exchange symbols, contract specs, liquidity, funding cadence, and available history may differ.

### Reconstruction Limitations

Generated coverage and real-data validation reports make these limitations explicit:

| Can validate from public APIs | Cannot recover from public APIs |
| --- | --- |
| OHLCV coverage for requested symbols and window | Original L2 order book snapshots |
| Funding-rate availability where the exchange exposes history | Original prompts, LLM calls, agent negotiations, and risk-manager approvals |
| Exploratory AZTE/CBD metrics derived from public candles | The paper's original SQLite dry-run database and trade provenance |

Treat this as reproduction of public market conditions, not reproduction of original agent decisions. The historical reconstruction can show what market data was available through public APIs and can compute deterministic derived metrics, but it cannot validate claims that depend on unreleased agent logs, L2 snapshots, prompts, or the original SQLite records.

## AZTE And CBD Metrics

After downloading candles, compute the paper's market-data-dependent trigger and diversification metrics from the SQLite store:

```bash
python scripts/compute_azte_cbd_metrics.py --db data/hyperliquid_ohlcv/market_data.sqlite
```

The command reads stored OHLCV closes, uses the paper defaults of a 30-bar rolling absolute-return baseline, `z >= 2.0`, and `abs_return >= 0.003`, and writes deterministic outputs under `data/hyperliquid_ohlcv/azte_cbd_metrics/`:

| File | Purpose |
| --- | --- |
| `azte_cbd_metrics.csv` | Per-symbol, per-bar metric rows after the first candle, including warmup status, rolling mean/std, z-score, trigger flag, BTC availability, `correlation_to_btc`, `rho_cb`, `z_tilde`, and `omega`. |
| `azte_cbd_events.csv` | Event-level subset containing only triggered AZTE rows for downstream validation. |
| `azte_cbd_summary.json` | Per-symbol row counts, warmup rows, trigger counts, CBD computed rows, and missing-BTC counts. |

Useful options:

```bash
python scripts/compute_azte_cbd_metrics.py --symbols BTC/USDC:USDC,ETH/USDC:USDC --btc-symbol BTC/USDC:USDC
python scripts/compute_azte_cbd_metrics.py --window 30 --z-threshold 2.0 --absolute-return-floor 0.003
python scripts/compute_azte_cbd_metrics.py --per-symbol
```

Warmup rows are retained and marked explicitly. CBD fields are populated only when a BTC candle exists at the same timestamp and enough aligned BTC/asset observations are available; otherwise `cbd_status` records the limitation.

## Real-Data Validation CLI

The paper-aggregate validation remains unchanged:

```bash
cd validation
python validate_claims.py --out results
```

After downloading market data, run the separate real-data validation mode against the SQLite store:

```bash
cd validation
python validate_claims.py --market-db ../data/hyperliquid_ohlcv/market_data.sqlite --out results
```

This writes `real_data_validation_report.md`, `real_data_validation_results.json`, and `real_data_validation_results.csv`. Coverage and funding availability are pass/fail or unsupported checks; AZTE/CBD outputs are exploratory reconstruction metrics. The report explicitly caveats that public OHLCV/funding data cannot recover original L2 order book snapshots, LLM decisions, or the paper's original SQLite dry-run logs.
