# Repository profile

## Purpose

This repository validates and approximates the AGENTICAITA Paper2Code workflow through static claim checks, public market-data reconstruction, AZTE/CBD metrics, and replication harness runs.

## Preferred broker path

Use the single-file patch-submission envelope broker.

Submit exactly one envelope file to the existing `patch-submissions` branch:

```text
.patches/inbox/<submission-id>.patch-submission
```

The broker creates the implementation branch and pull request.

## Preferred validation commands

Install dependencies when needed:

```bash
pip install -r requirements.txt
```

Run a small market-data smoke test when downloader changes are involved:

```bash
python scripts/fetch_hyperliquid_ohlcv.py --symbol-limit 3
```

Compute AZTE/CBD metrics when market-metric code changes are involved:

```bash
python scripts/compute_azte_cbd_metrics.py --symbols BTC/USDC:USDC,ETH/USDC:USDC
```

Run static claim validation when validation code changes are involved:

```bash
cd validation
python validate_claims.py --out results
```

Run real-data validation only when a suitable local market database exists:

```bash
cd validation
python validate_claims.py --market-db ../data/hyperliquid_ohlcv/market_data.sqlite --out results
```

## Generated and cache paths to avoid

Avoid committing generated market data, SQLite databases, coverage reports, validation outputs, replication results, local caches, bytecode, or local machine files.

Common exclusions:

- `data/`
- `replication/results*/`
- `validation/results/`
- `*.sqlite`
- `*.db`
- `coverage_report.*`
- `real_data_validation_results.*`
- `real_data_validation_report.md`
- `__pycache__/`
- `.pytest_cache/`
- `.coverage`
- `*.pyc`
- `.DS_Store`
- `.patches/`

## Issue and PR expectations

Use one GitHub issue per unit of work.

Use `Closes #...` only when the generated PR should close the issue after merge. Use `Addresses #...` for smoke tests, diagnostics, partial work, or PRs that may be closed unmerged.
