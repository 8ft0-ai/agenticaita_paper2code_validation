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

The default window is `2026-04-06T00:00:00Z` through `2026-04-11T23:59:59Z`, using `ccxt.hyperliquid` and `1m` candles. Raw per-symbol CSV files, `manifest.json`, `market_data.sqlite`, and coverage reports are written under `data/hyperliquid_ohlcv/`, which is intentionally ignored by git.

The SQLite database is created automatically. Its validation-facing schema is:

| Table | Purpose |
| --- | --- |
| `symbols` | Exchange symbol catalog with `exchange_id`, `symbol`, `market_type`, active status, and first/last seen timestamps. |
| `candles` | OHLCV candles keyed by `exchange_id`, `symbol`, `timeframe`, and `timestamp_ms`, plus UTC timestamp, OHLCV fields, and retrieval time. |
| `funding_rates` | Funding-rate storage keyed by `exchange_id`, `symbol`, and `timestamp_ms` for validation/backtest adapters that need funding context. |
| `fetch_metadata` | Per-symbol retrieval status with requested window, candle count, error text, CSV path, and retrieval time. |

After each run, `coverage_report.md` and `coverage_report.json` summarize candle counts, expected counts, missing interval samples, duplicate timestamps, unavailable symbols, and symbols with incomplete data.

Useful options:

```bash
python scripts/fetch_hyperliquid_ohlcv.py --symbols BTC/USDC:USDC,ETH/USDC:USDC --out data/hyperliquid_ohlcv_smoke
python scripts/fetch_hyperliquid_ohlcv.py --db data/hyperliquid_ohlcv/market_data.sqlite
python scripts/fetch_hyperliquid_ohlcv.py --max-retries 5 --retry-sleep 3 --limit 1000
```

Failures are recorded per symbol in `manifest.json`; one symbol failure does not abort the rest of the run.
