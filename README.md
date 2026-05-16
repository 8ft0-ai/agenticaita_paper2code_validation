# agenticaita_paper2code_validation
agenticaita_paper2code_validation

## Hyperliquid OHLCV Downloader

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
