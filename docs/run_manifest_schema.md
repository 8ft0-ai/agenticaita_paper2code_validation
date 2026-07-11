# Run Manifest Schema

`run_manifest.json` is the canonical machine-readable summary for a generated validation, quality-check, market-data, or replication run. It lets local indexers and dashboards inspect runs without parsing every generated CSV, SQLite database, or Markdown report.

Generated manifests are local artefacts by default. Commit them only when deliberately promoted into curated documentation.

## Schema version

Current schema version: `1`.

## Required fields

| Field | Meaning |
| --- | --- |
| `schema_version` | Manifest schema version. |
| `run_id` | Stable run identifier, usually the run directory name. |
| `scenario` | `static_validation`, `real_data_validation`, `replication`, `quality_check`, `market_data_coverage`, or `unknown`. |
| `commit_sha` | Commit used for the run, when known. |
| `command` | Command used for the run, when known. |
| `started_at`, `completed_at` | Optional ISO-8601 timestamps. |
| `status` | `pass`, `warning`, `fail`, or `unknown`. |
| `quality_status` | `pass`, `warning`, `fail`, `not_run`, or `unknown`. |
| `data` | Data provenance and coverage metrics. |
| `metrics` | Scenario-specific metrics. |
| `warnings` | Human-readable warnings and limitations. |
| `artefacts` | Relative paths to discovered reports, JSON, CSV, and SQLite artefacts. |
| `missing_artefacts` | Expected artefacts that were not present. |

## Status rules

Use `fail` for explicit failures, `warning` for qualified, unsupported, exploratory, incomplete, or missing-optional-output cases, `pass` for clean successful runs, and `unknown` when a run cannot be classified.

## Path rules

Manifest paths should be relative to the repository root or a supplied base directory. Avoid absolute local machine paths in shared or curated summaries.
