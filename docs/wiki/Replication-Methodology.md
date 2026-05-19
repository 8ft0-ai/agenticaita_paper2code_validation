# Replication Methodology

This page summarises how the repository separates static validation, functional replication, and empirical reconstruction.

## Validation path

The `validation/` path checks claims that can be tested from reported paper quantities. It covers arithmetic consistency, summary statistics, cost scenarios, binomial checks, CBD properties, and explicit unsupported markers for claims requiring unavailable raw artefacts.

Primary command:

```bash
cd validation
python validate_claims.py --out results
```

## Functional replication path

The `replication/` path runs an auditable dry-run approximation of the paper architecture. It includes AZTE triggers, CBD scoring, a sequential Analyst to Risk Manager to Executor pipeline, deterministic risk gates, IGP cooldowns, SQLite audit tables, and transaction-cost sensitivity.

Primary command:

```bash
python replication/replicate.py --config replication/config.yaml
```

## Real-data reconstruction path

The real-data path starts from public CCXT-compatible market data, exports complete candle coverage into a replication input CSV, and then runs the replication harness.

Primary command:

```bash
python scripts/run_real_data_replication.py --profile baseline-15 --exchange binanceusdm
```

Use the quality checker before interpreting generated outputs:

```bash
python scripts/check_replication_quality.py \
  --input-csv data/binanceusdm_ohlcv_real_subset/replication_input_ohlcv.csv \
  --results-dir replication/results_real_binanceusdm_real_subset \
  --real-data
```

## Interpretation rule

A successful functional or real-data run does not prove the original live dry-run. It shows whether the documented architecture can be executed and whether comparable public market-condition checks are internally coherent.
