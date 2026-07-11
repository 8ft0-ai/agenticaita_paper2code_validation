# GitHub Actions Results Surface

The `Results Surface Smoke` workflow exposes automated validation and deterministic replication smoke-run results directly in GitHub Actions.

## Where to view results

Open the workflow run and inspect the job summary. The summary includes status counts, one row per indexed run, key metrics, warnings, and generated artefact names.

The workflow also uploads a `run-results-<run-id>` artefact. Download it from the workflow run's **Artifacts** section to inspect:

- `run_manifest.json` files;
- validation reports and JSON/CSV results;
- deterministic replication `summary.json` and `replication_report.md`;
- `results_index.jsonl`;
- `results_index.md`;
- `results_dashboard.html`.

## Raw data policy

The workflow intentionally does not upload raw market-data SQLite databases, raw OHLCV CSV downloads, or large generated market-data directories. Those remain local or external artefacts under `docs/artifact_retention_policy.md`.

## Local summary rendering

To reproduce the Actions summary locally after generating a results index:

```bash
python scripts/write_github_step_summary.py \
  --index results_index.jsonl \
  --summary-file results_index.md \
  --dashboard results_dashboard.html \
  --out ci_step_summary.md
```

If `--out` is omitted, the script appends to `$GITHUB_STEP_SUMMARY` when that environment variable is present. Outside GitHub Actions, it prints the summary to stdout.

## Partial runs

The workflow builds the available manifests, index, dashboard, and summary even when validation or replication smoke steps fail. The job still fails at the end if either smoke command fails, but the uploaded artefact and job summary should contain the available diagnostics.
