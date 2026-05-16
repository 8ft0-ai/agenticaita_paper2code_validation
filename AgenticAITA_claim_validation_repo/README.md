# AGENTICAITA claim validation

This repository is a small Paper2Code-style implementation for validating the numerical and statistical claims in `2605.12532v1.pdf`.

It does not attempt to recreate the live trading system. The paper does not provide the raw SQLite database, exchange fills, market data, LLM call logs, funding-rate series, or production configuration. Instead, it validates the claims that are reproducible from the paper's reported quantities and flags claims that need missing artefacts.

## Run

```bash
python validate_claims.py --out results
pytest -q
```

To validate a downloaded market-data SQLite store separately from the paper aggregate checks:

```bash
python validate_claims.py --market-db ../data/hyperliquid_ohlcv/market_data.sqlite --out results
```

The real-data path keeps pass/fail checks limited to downloaded data coverage and funding availability. AZTE/CBD trigger and diversification rows are reported as exploratory reconstruction metrics because public market data cannot recover the original L2 order book snapshots, LLM decisions, or paper SQLite trade logs.

## Outputs

- `results/validation_report.md`
- `results/validation_results.json`
- `results/validation_results.csv`
- `results/real_data_validation_report.md` when `--market-db` is used
- `results/real_data_validation_results.json` when `--market-db` is used
- `results/real_data_validation_results.csv` when `--market-db` is used

## Interpretation

- `pass`: arithmetic/statistical value matches within tolerance.
- `qualified`: numerically close or correct under a stated interpretation, but the paper's wording is methodologically ambiguous.
- `unsupported`: cannot be independently verified without raw data or logs.
