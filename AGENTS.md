# AGENTS.md

## Project workflow

This repository uses the single-file `.patch-submission` envelope broker for implementation work.

Agents must not push materialised implementation or source changes directly to `main`.

Normal implementation work should be submitted as one envelope file under `.patches/inbox/` on the existing `patch-submissions` branch:

```text
.patches/inbox/<submission-id>.patch-submission
```

The broker validates the extracted patch, creates the implementation branch, opens the pull request, and archives the submission.

## Hard rules

- Do not create implementation branches or pull requests manually unless explicitly instructed.
- Do not push source-code, documentation, generated data, or result artefact changes directly to `main`.
- For normal implementation work, the only remote write is one commit to `patch-submissions` containing exactly one `.patch-submission` envelope file.
- Keep changes scoped to one GitHub issue.
- Do not submit another envelope while a previous submission is unresolved.
- Never resubmit a failed envelope unchanged; regenerate from current `origin/main` and use a fresh `-v2` or split submission id.

## Validation expectations

Select validation based on the changed area.

Dependency installation:

```bash
pip install -r requirements.txt
```

Market-data smoke test:

```bash
python scripts/fetch_hyperliquid_ohlcv.py --symbol-limit 3
```

AZTE/CBD metrics when relevant:

```bash
python scripts/compute_azte_cbd_metrics.py --symbols BTC/USDC:USDC,ETH/USDC:USDC
```

Static claim validation:

```bash
cd validation
python validate_claims.py --out results
```

Real-data validation when market data is available:

```bash
cd validation
python validate_claims.py --market-db ../data/hyperliquid_ohlcv/market_data.sqlite --out results
```

Report skipped validations explicitly.

## Generated data and artefacts

Do not commit generated market data, SQLite databases, coverage reports, replication outputs, validation results, local caches, bytecode, or large artefacts unless the issue explicitly asks for small fixtures.

Avoid committing:

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

## Skills and prompts

Use `.agents/repo-profile.md` for repository-specific constraints.

Use `.agents/skills/submitting-patches-through-envelope/SKILL.md` when submitting existing patches through the broker.

Use `.agents/prompts/single-file-patch-submission.md` for ChatGPT web sessions.
