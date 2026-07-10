# AGENTS.md

## Patch-submission workflow (primary path)

This repository uses the single-file `.patch-submission` envelope broker. Do not push source changes directly to `main`. Normal implementation work is submitted as one envelope file on the `patch-submissions` branch:

```text
.patches/inbox/<submission-id>.patch-submission
```

The broker validates the patch, creates the implementation branch, opens the PR, and archives the submission.

Hard rules:
- Do not create branches or PRs manually unless explicitly instructed.
- The only remote write is one commit to `patch-submissions` with exactly one `.patch-submission` file.
- Keep changes scoped to one GitHub issue. Do not submit while another submission is unresolved.
- Never resubmit a failed envelope unchanged; regenerate from `origin/main` and use a fresh `-v2` id.

Use `.agents/skills/submitting-patches-through-envelope/SKILL.md` for the full procedure.
Use `.agents/repo-profile.md` for repo-specific validation commands and generated-artefact exclusions.

## Architecture: three independent modules, no package

This repo is not an installable package. There is no `setup.py`, `pyproject.toml`, or shared package boundary.

- `validation/` — static claim audit and optional real-data validation
- `replication/` — functional architecture replication with a proper `src/agenticaita/` sub-package
- `scripts/` — standalone CLI tools (fetch, metrics, export, comparison, run orchestration, GitHub hygiene)

**`scripts/` is NOT a Python package** (no `__init__.py`). Scripts there can only be imported when their directory is on `sys.path`. Several modules work around this with `sys.path.insert()`:
- `validation/real_data_validation.py` injects `scripts/` to import `compute_azte_cbd_metrics` and `fetch_hyperliquid_ohlcv`
- Root-level `tests/` imports from `scripts.<module>` relying on directory adjacency

## Three separate requirements files

Install dependencies based on what you're touching:

```bash
pip install -r requirements.txt          # root: ccxt, pandas, PyYAML, scipy, tabulate
cd validation && pip install -r requirements.txt  # validation: scipy, pytest, PyYAML
cd replication && pip install -r requirements.txt # replication: numpy, pandas, PyYAML, pytest, tabulate
```

For most work, the root `requirements.txt` suffices. Add pytest to the root install when running tests.

## No lint or typecheck config

There is no `ruff.toml`, `pyproject.toml`, `setup.cfg`, `flake8`, or `mypy` configuration. The `.gitignore` references `.ruff_cache/` but there is no committed ruff config. CI does not run any linter or typechecker.

## Testing: three disjoint pytest suites

There is no unified pytest config, `pytest.ini`, or root conftest. Each suite runs independently:

```bash
pytest tests/ -q                        # root scripts tests (no conftest)
cd validation && pytest -q              # validation tests
cd replication && pytest -q             # replication tests
```

The CI workflow `results-surface.yml` does not run `pytest`. It runs validation and replication as smoke-tests:
```bash
cd validation && python validate_claims.py --out results
python replication/replicate.py --config replication/config.yaml --out replication/results_ci_synthetic
```

## Key CLI shortcuts

Static claim validation (no market data needed):
```bash
cd validation && python validate_claims.py --out results
```

Real-data validation (requires market DB):
```bash
cd validation && python validate_claims.py --market-db ../data/hyperliquid_ohlcv/market_data.sqlite --out results
```

Market-data smoke test:
```bash
python scripts/fetch_hyperliquid_ohlcv.py --symbol-limit 3
```

AZTE/CBD metrics:
```bash
python scripts/compute_azte_cbd_metrics.py --symbols BTC/USDC:USDC,ETH/USDC:USDC
```

Replication dry-run (synthetic data, no input CSV):
```bash
python replication/replicate.py --config replication/config.yaml --out replication/results_ci_synthetic
```

Replication with real data (requires exported CSV):
```bash
python replication/replicate.py --config replication/config.yaml --input-csv <path> --out <dir>
```

LLM live smoke path (uses OpenRouter when `OPENROUTER_API_KEY` is set; otherwise exercises the deterministic fallback path and writes a skip/fallback reason):
```bash
cd replication && python llm_live_smoke.py --out results_llm_live_smoke
```

Strict CI-style skip when no live key is available:
```bash
cd replication && python llm_live_smoke.py --out results_llm_live_smoke --skip-without-key
```

Smoke outputs are written under `results_llm_live_smoke/`, including `pipeline_log.csv`, `llm_audit.jsonl`, and `smoke_status.json`.

Full automated real-data pipeline:
```bash
python scripts/run_real_data_replication.py --profile baseline-15 --exchange binanceusdm --timeframe 1m --start 2026-04-06T00:00:00Z --end 2026-04-11T23:59:59Z --config replication/config.yaml
```

## Two separate config files

`validation/config.yaml` and `replication/config.yaml` have different schemas. They are not shared.

## CI expectations

- `results-surface.yml` runs on PRs touching `docs/`, `replication/`, `scripts/`, `tests/`, or `validation/` — it runs both static validation and synthetic replication as smoke checks and fails on non-zero exit.
- `patch-submission-envelope-broker.yml` triggers on push to `patch-submissions` branch matching `.patches/inbox/*.patch-submission`.
- `paper-window-real-data.yml` is workflow_dispatch only (manual real-data replication).
- No workflow runs pytest or lint.

## Issue and PR conventions

- Use `Closes #N` for PRs that should close the issue after merge. Use `Addresses #N` for smoke tests, diagnostics, or PRs that may be closed unmerged.
- For historical-data reconstruction work, explicitly note that public APIs cannot recover original L2 snapshots, LLM decisions, or the paper's SQLite logs.