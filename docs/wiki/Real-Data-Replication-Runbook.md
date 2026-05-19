# Real-Data Replication Runbook

This page stages the Wiki version of the public-market replication workflow.

## Install dependencies

```bash
pip install -r requirements.txt
```

## Baseline workflow

Run the 15-symbol baseline subset against Binance USD-M fallback data:

```bash
python scripts/run_real_data_replication.py --profile baseline-15 --exchange binanceusdm
```

The script performs three stages:

1. fetch public one-minute OHLCV and available funding history;
2. export complete SQLite candle coverage to replication input CSV;
3. run the functional replication harness with `replication/config.yaml`.

## Larger universe workflow

```bash
python scripts/run_real_data_replication.py --profile large --exchange binanceusdm --symbol-limit 76
```

The large profile can take substantially longer because it may fetch many active markets before selecting complete symbols.

## Existing database workflow

```bash
python scripts/run_real_data_replication.py \
  --skip-fetch \
  --skip-replication \
  --market-db data/binanceusdm_ohlcv_real_subset/market_data.sqlite \
  --replication-input data/binanceusdm_ohlcv_real_subset/replication_input_ohlcv.csv
```

## Quality checks

```bash
python scripts/check_replication_quality.py \
  --input-csv data/binanceusdm_ohlcv_real_subset/replication_input_ohlcv.csv \
  --results-dir replication/results_real_binanceusdm_real_subset \
  --real-data
```

The checker fails malformed input and empty real-data pipeline logs. Empty trades are warnings, not failures.

## Output retention

Generated data, SQLite stores, exported CSVs, replication result directories, and coverage reports remain local artefacts unless they are deliberately promoted into reviewed documentation under `docs/`.
