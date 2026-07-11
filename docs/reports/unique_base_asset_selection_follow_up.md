# Unique Base-Asset Large-Universe Follow-Up

Date: 2026-07-11

## Status

The large-universe exporter now selects contracts by distinct normalised base asset before applying the requested limit. This corrects the earlier behaviour in which 76 source contracts normalised to only 69 input assets.

The repository does not contain the downloaded Binance USD-M SQLite market database, so the corrected 76-asset run cannot be executed in CI or reconstructed from committed files. This is intentional under the artifact-retention policy. The workflow now records a precise blocker and the available maximum when the local database contains fewer than the requested number of complete unique assets.

## Selection Policy

For each normalised base asset, the exporter chooses one complete source contract using this deterministic order:

1. the explicitly required benchmark symbol;
2. USDT quote;
3. USDC quote;
4. another USD-like quote;
5. other quotes;
6. linear settlement before inverse settlement;
7. lexical source-symbol order as the final tie-breaker.

BTC remains first priority when `--required-symbol BTC/USDT:USDT` is complete.

## Local Rerun Using the Existing Database

```bash
python scripts/run_real_data_replication.py \
  --profile large \
  --exchange binanceusdm \
  --symbol-limit 76 \
  --skip-fetch \
  --market-db data/binanceusdm_ohlcv_large_76/market_data.sqlite \
  --start 2026-04-06T00:00:00Z \
  --end 2026-04-11T23:59:59Z
```

The corrected workflow writes:

```text
data/binanceusdm_ohlcv_large_76_unique_assets/complete_symbols_76.txt
data/binanceusdm_ohlcv_large_76_unique_assets/complete_assets_76.txt
data/binanceusdm_ohlcv_large_76_unique_assets/replication_input_ohlcv.csv
replication/results_real_binanceusdm_large_76_unique_assets/
```

When fewer than 76 complete unique base assets are available, the workflow stops before replication and reports the exact available count together with the symbol and asset-list paths. It does not silently substitute duplicate contracts.

## Interpretation Boundary

A 76-asset input universe is not equivalent to 76 unique traded assets. The regenerated report must record separately:

- selected source-symbol count;
- distinct normalised input-asset count;
- distinct traded-asset count.

No admission, signal, risk, or execution parameter is changed to force trades across all selected assets.
