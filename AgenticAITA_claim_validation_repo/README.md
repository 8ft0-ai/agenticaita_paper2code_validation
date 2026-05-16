# AGENTICAITA claim validation

This repository is a small Paper2Code-style implementation for validating the numerical and statistical claims in `2605.12532v1.pdf`.

It does not attempt to recreate the live trading system. The paper does not provide the raw SQLite database, exchange fills, market data, LLM call logs, funding-rate series, or production configuration. Instead, it validates the claims that are reproducible from the paper's reported quantities and flags claims that need missing artefacts.

## Run

```bash
python validate_claims.py --out results
pytest -q
```

## Outputs

- `results/validation_report.md`
- `results/validation_results.json`
- `results/validation_results.csv`

## Interpretation

- `pass`: arithmetic/statistical value matches within tolerance.
- `qualified`: numerically close or correct under a stated interpretation, but the paper's wording is methodologically ambiguous.
- `unsupported`: cannot be independently verified without raw data or logs.
