# Run Results Dashboard

`results_dashboard.html` is a local, static HTML view over `results_index.jsonl`. It is intended for quickly reviewing validation, market-data, quality-check, and replication runs without committing raw generated artefacts.

## Usage

Generate an index first:

```bash
python scripts/index_run_results.py \
  --runs validation/results* replication/results* data/*_ohlcv* \
  --out-jsonl results_index.jsonl \
  --out-md results_index.md
```

Render the dashboard:

```bash
python scripts/render_results_dashboard.py \
  --index results_index.jsonl \
  --out results_dashboard.html
```

Open `results_dashboard.html` in a browser. The dashboard is self-contained and does not require network access.

## Dashboard contents

The dashboard includes:

- summary cards for pass, warning, fail, and unknown statuses;
- grouped run tables for static validation, real-data validation, market-data coverage, replication, quality checks, and unknown entries;
- local links to discovered artefacts such as validation reports, coverage reports, `summary.json`, replication reports, and quality-check output;
- simple visual summaries for status counts, symbol coverage, trade count, and net PnL where those metrics are present.

## Retention

The dashboard is generated output and remains local by default. Do not commit `results_dashboard.html` unless a specific result is deliberately promoted into curated documentation under `docs/`.
