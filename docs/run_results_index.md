# Run Results Index

`results_index.jsonl` and `results_index.md` provide a local overview of generated validation, market-data, quality-check, and replication runs.

The indexer reads existing run directories and prefers `run_manifest.json` when present. When a manifest is missing, it falls back to recognised repository outputs such as `summary.json`, `validation_results.json`, `real_data_validation_results.json`, `quality_report.json`, and `coverage_report.json`.

## Usage

```bash
python scripts/index_run_results.py \
  --runs validation/results* replication/results* data/*_ohlcv* \
  --out-jsonl results_index.jsonl \
  --out-md results_index.md
```

You can also index a single run directory:

```bash
python scripts/index_run_results.py \
  --runs replication/results_real_binanceusdm_real_subset \
  --out-jsonl results_index.jsonl \
  --out-md results_index.md
```

## Outputs

| File | Purpose |
| --- | --- |
| `results_index.jsonl` | One full manifest-style JSON object per discovered run. |
| `results_index.md` | Human-readable table with run id, scenario, status, quality status, commit SHA, window, symbol counts, trade count, net PnL, warnings, and artefact links. |

Generated index files are local artefacts by default. Do not commit them unless they are deliberately promoted into a curated report under `docs/`.

## Failure handling

Malformed run directories and invalid manifests are represented as warning entries rather than crashing the whole index. This makes it possible to review partial or failed runs alongside successful runs.
