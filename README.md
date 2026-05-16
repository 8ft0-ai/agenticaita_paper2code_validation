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

The default window is `2026-04-06T00:00:00Z` through `2026-04-11T23:59:59Z`, using `ccxt.hyperliquid` and `1m` candles. Raw per-symbol CSV files plus `manifest.json` are written under `data/hyperliquid_ohlcv/`, which is intentionally ignored by git.

Useful options:

```bash
python scripts/fetch_hyperliquid_ohlcv.py --symbols BTC/USDC:USDC,ETH/USDC:USDC --out data/hyperliquid_ohlcv_smoke
python scripts/fetch_hyperliquid_ohlcv.py --max-retries 5 --retry-sleep 3 --limit 1000
```

Failures are recorded per symbol in `manifest.json`; one symbol failure does not abort the rest of the run.
