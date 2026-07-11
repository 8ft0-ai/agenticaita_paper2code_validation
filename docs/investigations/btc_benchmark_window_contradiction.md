# BTC Benchmark Window Contradiction

Date: 2026-07-11

## Finding

**Status: divergent and unresolved.**

The paper reports a passive BTC-perpetual price loss of approximately 15% over its disclosed five-day evaluation window, 6–11 April 2026. The repository's complete Binance USD-M one-minute reconstruction for that window instead records BTC increasing from 69,102.9 to 73,013.4, a start-to-end price return of approximately **+5.659%**.

These two claims differ by about 20.66 percentage points and have opposite directions. Funding payments can change a perpetual position's total return, but they do not change the direction of the paper's separately stated price-only move.

## Paper Claim

The paper states that:

- the dry-run session spanned five days, 6–11 April 2026;
- a passive BTC perpetual over the same window would have lost approximately 15% on capital;
- this corresponds to approximately –US$3,912 on US$26,079 equivalent notional;
- the reported strategy alpha versus BTC was +14.94 percentage points;
- funding in contango would make the passive long benchmark worse than the price-only baseline.

The same –15% correction description is repeated in the benchmark table, discussion, limitations, and conclusion. The paper does not disclose the exact benchmark timestamps, source venue, contract, candle convention, entry price, exit price, or funding-rate series needed to reconstruct the calculation.

## Repository Calculation

The completed Binance USD-M fallback run records:

| Field | Value |
| --- | ---: |
| Evaluation window | `2026-04-06T00:00:00Z` to `2026-04-11T23:59:59Z` |
| BTC first close | 69,102.9 |
| BTC last close | 73,013.4 |
| Start-to-end return | +5.658952% |
| Equivalent notional | US$26,132.00 |
| Price-only benchmark PnL | +US$1,478.80 |

Formula:

```text
start_to_end_return = (73,013.4 / 69,102.9) - 1
                    = +5.658952%
```

Applying the paper's claimed –15% return to the repository start price would imply an end price of approximately US$58,737, which is inconsistent with the observed end close and with contemporaneous public reporting.

## Independent Directional Cross-Check

Two contemporaneous public reports independently support an upward, not downward, move across the disclosed dates:

- Investopedia reported on 6 April 2026 that Bitcoin was trading near US$70,000 after rallying over the preceding weekend: <https://www.investopedia.com/5-things-to-know-before-the-stock-market-opens-april-6-2026-11943235>
- The Economic Times reported on 11 April 2026 that Bitcoin was trading around US$72,757 after moving into the US$73,000 area: <https://m.economictimes.com/markets/cryptocurrency/bitcoin-climbs-to-73k-after-rangebound-move-softer-cpi-data-supports-upside/articleshow/130189039.cms>

These reports are not substitutes for exact minute candles, but they independently corroborate the direction and approximate price levels shown by the Binance reconstruction. They do not support a 15% start-to-end loss over 6–11 April.

## Alternative Interpretations Tested

### Start-to-end return

The disclosed UTC window produces +5.659% on the reconstructed Binance data. This directly contradicts a –15% buy-and-hold price return.

### Peak-to-trough drawdown

A peak-to-trough drawdown is a different statistic from buy-and-hold return. The repository now includes `scripts/analyse_btc_benchmark_window.py` to calculate both measures separately from an OHLCV file. Even if an intraperiod drawdown approached 15%, it would not justify describing the same-window passive start-to-end result as a 15% price loss without explicitly changing the benchmark definition.

### Timezone and daily-close boundaries

The contemporaneous price levels near US$70,000 on 6 April and near US$73,000 on 11 April make it unlikely that an ordinary timezone shift or daily-close convention would reverse the result to approximately –15%. Exact author timestamps are still required to rule out an undisclosed narrower interval.

### Funding adjustment

The paper distinguishes the –15% price baseline from a funding-adjusted result that is said to be worse. Funding can reduce a long perpetual's PnL, but the paper provides neither the funding series nor position-timing details. It cannot reconcile the stated price move itself, and no funding-adjusted equivalence is claimed by this repository.

### Venue substitution

BTC prices can differ modestly across venues, but a venue basis is not a plausible explanation for a roughly 20.66 percentage-point directional difference over the same dates. Exact Hyperliquid candles for the expired window are unavailable through the public candle endpoint, so the venue-specific benchmark remains unresolved rather than reproduced.

## Reproduction Command

For a local OHLCV artefact:

```bash
python scripts/analyse_btc_benchmark_window.py \
  --input replication/results_real_binanceusdm_large_76/ohlcv_used.csv \
  --asset BTC \
  --notional-usd 26079 \
  --out btc_benchmark_window_analysis.json
```

The output reports start-to-end return, full-window high-to-low range, time-ordered maximum drawdown, trough-to-end recovery, and price-only benchmark PnL as separate fields.

## Evidence Classification

| Claim | Status | Rationale |
| --- | --- | --- |
| BTC lost approximately 15% from the start to end of 6–11 April 2026 | **Divergent** | Complete Binance one-minute reconstruction gives +5.659%; contemporaneous reports support the same direction. |
| An intraperiod BTC drawdown may have occurred | **Unresolved** | Must be calculated from a retained OHLCV artefact and must not be substituted for start-to-end return. |
| Funding made a passive BTC perpetual materially worse | **Unresolved** | Exact funding series, contract, timing, and sizing are not disclosed. |
| Strategy produced +14.94 percentage points alpha versus BTC | **Unsupported from available evidence** | The reported alpha depends on the contradictory benchmark and unavailable funding details. |

## Clarification Required from the Authors

A reproducible reconciliation requires:

1. exact UTC entry and exit timestamps;
2. benchmark venue and contract symbol;
3. entry and exit prices and candle convention;
4. whether –15% means start-to-end return or peak-to-trough drawdown;
5. funding timestamps, rates, position size, and formula inputs;
6. the calculation that maps –US$3,912 on US$26,079 to the reported +14.94 percentage-point alpha.

Until those details are supplied, the appropriate conclusion is a material benchmark contradiction, not evidence of misconduct and not a resolved venue difference.
