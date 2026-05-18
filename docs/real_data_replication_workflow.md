# Real-Data Replication Workflow

This runbook documents the single scripted entry point for the public-market AGENTICAITA replication workflow.

The script runs three existing repository stages:

1. fetch public one-minute OHLCV and available funding history with `scripts/fetch_hyperliquid_ohlcv.py`;
2. export complete SQLite candle coverage to replication input CSV with `scripts/export_replication_input.py`;
3. run the functional replication harness with `replication/replicate.py` and `replication/config.yaml`.

Generated market data, exported CSVs, replication outputs, SQLite databases, and coverage reports remain local artefacts under the repository artifact-retention policy.

## Dependencies and runtime

Install the normal project dependencies before running the workflow:

```bash
pip install -r requirements.txt
```

The fetch stage uses CCXT and public exchange APIs. A baseline run should be treated as a multi-minute to tens-of-minutes workflow because it downloads a five-day, one-minute window plus available funding metadata. A large-universe run can take substantially longer.

## Baseline 15-symbol workflow

The default profile is the 15-symbol baseline subset used for AGENTICAITA reconstruction work. The default exchange is Binance USD-M because the documented Hyperliquid paper-window attempt returned funding rows but no OHLCV candles.

```bash
python scripts/run_real_data_replication.py --profile baseline-15 --exchange binanceusdm
```

The profile maps the baseline assets to the selected exchange quote convention. For Binance USD-M it requests symbols such as `BTC/USDT:USDT`; for Hyperliquid it requests `BTC/USDC:USDC`.

## Larger universe workflow

Use the `large` profile when exploring a broader public-market universe. The export step selects only symbols with complete candle coverage for the requested window and prioritises BTC before applying the symbol limit.

```bash
python scripts/run_real_data_replication.py --profile large --exchange binanceusdm --symbol-limit 76
```

## Existing database and smoke-check mode

Use `--skip-fetch` when a market-data SQLite store already exists. Use `--skip-replication` when only the input-conversion path should be exercised.

```bash
python scripts/run_real_data_replication.py \
  --skip-fetch \
  --skip-replication \
  --market-db data/binanceusdm_ohlcv_real_subset/market_data.sqlite \
  --replication-input data/binanceusdm_ohlcv_real_subset/replication_input_ohlcv.csv
```

Use `--dry-run` to inspect the resolved paths and commands without creating outputs.
