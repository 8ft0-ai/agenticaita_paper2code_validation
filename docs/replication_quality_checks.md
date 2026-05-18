# Replication Quality Checks

Use `scripts/check_replication_quality.py` before interpreting generated real-data replication outputs. The checker is intentionally separate from generated output directories so it can be run against existing local artefacts without committing those artefacts.

## Checks

The input CSV checks are always applied:

- the OHLCV input is non-empty;
- required columns are present: `timestamp`, `asset`, and `close`;
- there are no duplicate `(timestamp, asset)` rows.

When `--results-dir` is supplied, the checker also validates generated outputs:

- `pipeline_log.csv` exists and has required columns when non-empty;
- `pipeline_log.csv` is non-empty for real-data runs;
- `trades.csv` has required columns when trades are present;
- an empty `trades.csv` is reported as a warning rather than a failure;
- `replication_report.md` exists and is non-empty.

## Examples

Validate a generated real-data run:

```bash
python scripts/check_replication_quality.py \
  --input-csv data/binanceusdm_ohlcv_real_subset/replication_input_ohlcv.csv \
  --results-dir replication/results_real_binanceusdm_real_subset \
  --real-data
```

Validate only an exported replication input CSV:

```bash
python scripts/check_replication_quality.py \
  --input-csv data/binanceusdm_ohlcv_real_subset/replication_input_ohlcv.csv
```

## Exit behaviour

The checker exits with status `0` when all required checks pass. Warnings, such as an empty `trades.csv`, are printed to stderr and included in the JSON output but do not fail the command.

The checker exits with status `2` when one or more required checks fail. The error message starts with `replication quality check failed:` so automation can distinguish quality failures from Python tracebacks.
