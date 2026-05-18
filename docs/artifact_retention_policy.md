# Artifact Retention Policy

This repository treats generated market data, validation outputs, and replication run directories as reproducible local artefacts unless they are explicitly promoted into reviewed documentation. The goal is to keep git small, auditable, and focused on source files, configuration, tests, runbooks, and curated evidence.

## Default retention rule

Generated outputs stay out of git by default. A generated file should be committed only when it is intentionally converted into a compact, reviewer-facing artefact with enough provenance to be reproduced from public commands or external storage.

Prefer this split:

| Keep in git | Keep local or external |
| --- | --- |
| Source code, tests, configuration, prompts, runbooks, and curated Markdown reports. | Raw OHLCV CSVs, SQLite databases, full replication output directories, validation result directories, coverage dumps, cache directories, and broker archives. |
| Small fixtures that are required by tests and are committed under a test fixture path. | Downloaded exchange data, full `pipeline_log.csv`, `trades.csv`, `vol_history.csv`, generated `summary.json`, generated replication reports, and ad hoc notebook or coverage outputs. |
| Documentation that summarises a run, states its limitations, and links back to reproducible commands. | Large or transient data needed only to reproduce a local analysis run. |

## Generated artefacts that remain gitignored

The following generated artefacts should remain ignored and should not be committed from normal validation or replication runs:

| Path or pattern | Retention decision | Rationale |
| --- | --- | --- |
| `data/` | Local or external only. | Contains raw public market downloads, generated SQLite stores, exported replication inputs, manifests, and coverage reports. |
| `replication/results*/` | Local or external only. | Contains full replication audit outputs, generated reports, CSV logs, and SQLite audit databases. |
| `validation/results*/` | Local or external only. | Contains generated static and real-data validation outputs. |
| `*.sqlite`, `*.db` | Local or external only. | Binary databases are often large and are generated from reproducible commands. |
| `coverage_report.*` | Local unless promoted to `docs/`. | Coverage reports are generated per run; commit only a curated summary when it supports a reviewed result. |
| `real_data_validation_results.*` and `real_data_validation_report.md` | Local unless promoted to `docs/`. | These are generated validation outputs. A stable, edited report belongs under `docs/`, not in the command output path. |
| `.patches/` | Broker branch only. | Normal implementation patches must not include broker inbox, processed, or failed archives. |
| `__pycache__/`, `.pytest_cache/`, `.coverage`, `*.pyc`, `.DS_Store` | Local only. | Runtime caches and local machine files. |

## Summaries and reports that may be committed

Commit a generated finding only after turning it into a stable repository artefact. Suitable committed outputs include:

- curated Markdown reports under `docs/` that explain a validation or replication result;
- small comparison tables or summaries that are directly cited by documentation;
- small deterministic test fixtures under `tests/fixtures/` when they are required for automated tests;
- runbooks that describe commands, inputs, limitations, and expected local outputs.

A committed summary or report should state:

1. the command or workflow used to create the source output;
2. the market venue, symbol universe, timeframe, and date window;
3. whether the source data is public, locally generated, or externally archived;
4. the exact local output directory name used for the run;
5. any limitations that prevent the result from reproducing the original paper artefacts.

Do not commit raw generated JSON, CSV, SQLite, or run-directory contents merely because they were produced by a successful run. Promote only the smallest useful summary needed for review.

## Local run-output naming conventions

Use predictable, lower-case directory names with no spaces. Include the venue and scope in the path so a later reader can understand the run without opening the database.

Recommended market-data output names:

```text
data/<exchange>_ohlcv_<scope>/
data/hyperliquid_ohlcv_smoke/
data/hyperliquid_ohlcv_real_subset/
data/binanceusdm_ohlcv_real_subset/
data/binanceusdm_ohlcv_large_76/
data/bybit_ohlcv_large_<symbol-count>/
```

Recommended replication output names:

```text
replication/results_<scenario>_<venue>_<scope>/
replication/results_real_binance_subset/
replication/results_real_binance_calibrated/
replication/results_real_binance_large_76/
replication/results_calibration_sweep_<short-topic>/
```

Recommended validation output names:

```text
validation/results/
validation/results_static_<short-topic>/
validation/results_real_<venue>_<scope>/
```

Use these scope terms consistently:

| Scope term | Meaning |
| --- | --- |
| `smoke` | Small, fast run intended only to verify that the command path works. |
| `real_subset` | The 15-symbol baseline public-market subset used for AGENTICAITA reconstruction work. |
| `large_<n>` | Larger public-market universe with `<n>` complete symbols. |
| `calibrated` | A run using the calibrated replication configuration. |
| `calibration_sweep_<short-topic>` | Parameter sweep or diagnostic run. |

Append a date such as `_20260518` only when repeated local runs of the same scope need to coexist. Prefer a short issue or experiment slug over an opaque timestamp when the run is associated with a tracked issue.

## External storage guidance

Use external storage for raw or large artefacts that are useful for audit but unsuitable for git, such as full market databases, complete replication result directories, or broker archives. When external artefacts are retained, commit only a small pointer or report under `docs/` that records the storage location, checksum if available, generation command, and retention owner.

## Pre-commit checklist

Before committing a file produced by a validation or replication command, confirm that:

- it is not under `data/`, `replication/results*/`, `validation/results*/`, or `.patches/`;
- it is not a SQLite database, full generated CSV log, coverage dump, bytecode file, cache, or local machine file;
- it has been intentionally promoted into `docs/` or a test fixture path;
- it includes enough context for a reviewer to understand and reproduce the source run;
- it does not contain raw exchange data, private credentials, local absolute paths, or unreleased author artefacts.
