# AGENTICAITA Replication Report

## Executive Summary

This report documents the replication work performed for the AGENTICAITA Paper2Code validation repository. The goal was to move beyond static claim validation and run the executable replication harness on market data that is as close as practical to the paper's stated setup.

The final result is a functional architecture replication, not an empirical reproduction of the original five-day live dry-run. The harness can execute the published architecture pattern and can be calibrated to produce paper-like aggregate behavior, but it cannot validate the original live counts or decisions without the authors' original artefacts.

The calibrated real-data run is materially closer to the paper than the first real-data run:

| Metric | Initial Real-Data Run | Calibrated Real-Data Run | Paper Reported |
| --- | ---: | ---: | ---: |
| Total invocations | 277 | 169 | 157 |
| Trades executed | 265 | 153 | 139 |
| Agentic friction | 6.86% | 12.43% | 11.46% |
| Win rate | 43.02% | 47.71% | 51.80% |
| Profit factor | 0.672 | 0.841 | 0.841 |
| Net PnL | -$37.32 | -$9.34 | -$15.07 |

The main conclusion is that the architecture is executable and can produce comparable aggregate behavior on public market data after admission-control calibration. The result supports plausibility of the architecture and aggregate shape, but it does not independently prove the paper's empirical live-session claims.

## Repository Context

The repository now separates two complementary paths:

| Directory | Role | Question Answered |
| --- | --- | --- |
| `validation/` | Static claim validation | Are the paper's reported numbers internally consistent, and which claims are unsupported without missing artefacts? |
| `replication/` | Functional architecture replication | Can an auditable dry-run system matching the published architecture generate comparable artefacts? |

The work in this report concerns `replication/`.

The replication harness implements:

| Component | Harness Behavior |
| --- | --- |
| AZTE | Rolling absolute-return z-score trigger with an absolute-return floor. |
| CBD | Correlation-break diversification score using BTC as benchmark. |
| SDP | Sequential Analyst -> Risk Manager -> Executor pipeline. |
| Risk gates | Confidence, stop-loss, and position-size gates. |
| IGP | Global and per-asset cooldowns controlling admitted invocations. |
| Audit outputs | `pipeline_log.csv`, `trades.csv`, `vol_history.csv`, SQLite audit DB, JSON summary, Markdown report. |
| Cost sensitivity | Paper-style notional round-trip cost scenarios. |

## Data Plan

The data plan followed `CustomGPT/Paper2Code/data.md`.

The paper states that the original evaluation used:

| Required Input | Purpose |
| --- | --- |
| 1-minute OHLCV candles | AZTE trigger and analyst context. |
| L2 order book snapshots | Analyst reasoning and execution context. |
| Funding rate | Perpetual futures context and benchmark adjustments. |
| Ticker / market snapshot | Entry price and market context. |
| BTC price history | CBD decorrelation score. |
| SQLite memory tables | Volatility history, trades, audit logs, and episodic memory. |

The original paper artefacts were not available, so the replication used public historical candles and funding data where available. The report should therefore be interpreted as market-condition replication plus deterministic proxy-agent execution, not reconstruction of the original agent decisions.

## Hyperliquid Attempt

The first attempt used Hyperliquid perpetuals because `data.md` identifies Hyperliquid as the closest practical venue to the paper's unnamed decentralized perpetual-futures exchange.

Requested window:

```text
2026-04-06T00:00:00Z to 2026-04-11T23:59:59Z
```

Requested timeframe:

```text
1m
```

Requested symbols:

```text
BTC/USDC:USDC
ETH/USDC:USDC
SOL/USDC:USDC
AVAX/USDC:USDC
DOGE/USDC:USDC
ADA/USDC:USDC
XRP/USDC:USDC
DOT/USDC:USDC
FARTCOIN/USDC:USDC
XPL/USDC:USDC
CC/USDC:USDC
HEMI/USDC:USDC
S/USDC:USDC
BCH/USDC:USDC
ETC/USDC:USDC
```

Command used:

```bash
./.venv/bin/python scripts/fetch_hyperliquid_ohlcv.py \
  --symbols "BTC/USDC:USDC,ETH/USDC:USDC,SOL/USDC:USDC,AVAX/USDC:USDC,DOGE/USDC:USDC,ADA/USDC:USDC,XRP/USDC:USDC,DOT/USDC:USDC,FARTCOIN/USDC:USDC,XPL/USDC:USDC,CC/USDC:USDC,HEMI/USDC:USDC,S/USDC:USDC,BCH/USDC:USDC,ETC/USDC:USDC" \
  --out data/hyperliquid_ohlcv_real_subset \
  --max-retries 2 \
  --retry-sleep 1
```

Outcome:

| Result | Value |
| --- | ---: |
| Requested symbols | 15 |
| Successful symbol fetches | 15 |
| OHLCV candles per symbol | 0 |
| Funding rows per symbol | 144 |

Hyperliquid returned funding rows but no OHLCV candles for the requested historical window. This made the Hyperliquid data unusable for the replication harness, which currently requires candle closes.

Generated local artefacts:

```text
data/hyperliquid_ohlcv_real_subset/manifest.json
data/hyperliquid_ohlcv_real_subset/coverage_report.md
data/hyperliquid_ohlcv_real_subset/market_data.sqlite
```

## Binance USD-M Fallback

Following the fallback guidance in `data.md`, Binance USD-M futures were used as a comparable public perpetual-futures source.

Requested symbols were mapped from USDC-style Hyperliquid symbols to Binance USD-M `USDT` perpetual symbols:

```text
BTC/USDT:USDT
ETH/USDT:USDT
SOL/USDT:USDT
AVAX/USDT:USDT
DOGE/USDT:USDT
ADA/USDT:USDT
XRP/USDT:USDT
DOT/USDT:USDT
FARTCOIN/USDT:USDT
XPL/USDT:USDT
CC/USDT:USDT
HEMI/USDT:USDT
S/USDT:USDT
BCH/USDT:USDT
ETC/USDT:USDT
```

Command used:

```bash
./.venv/bin/python scripts/fetch_hyperliquid_ohlcv.py \
  --exchange binanceusdm \
  --symbols "BTC/USDT:USDT,ETH/USDT:USDT,SOL/USDT:USDT,AVAX/USDT:USDT,DOGE/USDT:USDT,ADA/USDT:USDT,XRP/USDT:USDT,DOT/USDT:USDT,FARTCOIN/USDT:USDT,XPL/USDT:USDT,CC/USDT:USDT,HEMI/USDT:USDT,S/USDT:USDT,BCH/USDT:USDT,ETC/USDT:USDT" \
  --out data/binanceusdm_ohlcv_real_subset \
  --max-retries 2 \
  --retry-sleep 1
```

Coverage result:

| Field | Value |
| --- | ---: |
| Exchange | `binanceusdm` |
| Timeframe | `1m` |
| Window | `2026-04-06T00:00:00Z` to `2026-04-11T23:59:59Z` |
| Symbols | 15 |
| Expected candles per symbol | 8,640 |
| Actual candles per symbol | 8,640 |
| Total candles | 129,600 |
| Missing intervals | 0 |
| Duplicate timestamps | 0 |
| Funding rows | 18 or 36 per symbol |

The Binance fallback produced complete one-minute OHLCV coverage for every requested symbol.

Generated local artefacts:

```text
data/binanceusdm_ohlcv_real_subset/manifest.json
data/binanceusdm_ohlcv_real_subset/coverage_report.md
data/binanceusdm_ohlcv_real_subset/market_data.sqlite
```

## Replication Input Preparation

The replication harness accepts a close-only CSV with the columns:

```text
timestamp,asset,close
```

It also accepts a fuller OHLCV CSV with the columns:

```text
timestamp,asset,open,high,low,close,volume
```

The Binance candle database was converted into the close-only format for the runs in this report. Symbols were normalized to base assets so that the harness's configured benchmark asset `BTC` would match the BTC rows.

Output:

```text
data/binanceusdm_ohlcv_real_subset/replication_input.csv
```

Rows:

```text
129,600
```

The dedicated export helper can now emit either close-only or full-OHLCV input. The calibrated runs in this report used close-only input. Subsequent OHLCV execution work uses full-OHLCV input to simulate stop-loss and take-profit exits over future bars with a conservative stop-loss-first tie-breaker when both thresholds are touched in the same candle.

Replication outputs now include a `metadata` block in `summary.json` and a `Run Metadata` section in `replication_report.md`. These record the data source, asset and candle counts, provenance columns such as exchange and source symbol when available, config values, execution mode, and git commit SHA when available.

## Initial Real-Data Replication Run

The first real-data run used the original replication defaults:

| Parameter | Initial Value |
| --- | ---: |
| `igp.global_cooldown_seconds` | 1800 |
| `igp.per_asset_cooldown_seconds` | 300 |
| `azte.z_threshold` | 2.0 |
| `azte.absolute_return_floor` | 0.003 |
| `risk.confidence_gate` | 0.60 |

Command used:

```bash
./.venv/bin/python replication/replicate.py \
  --config replication/config.yaml \
  --input-csv data/binanceusdm_ohlcv_real_subset/replication_input.csv \
  --out replication/results_real_binance_subset
```

Results:

| Metric | Initial Real-Data Run | Paper Reported | Delta |
| --- | ---: | ---: | ---: |
| Total invocations | 277 | 157 | +120 |
| Trades executed | 265 | 139 | +126 |
| Risk approved | 265 | 139 | +126 |
| Risk rejected | 12 | 5 | +7 |
| Analyst wait | 7 | 13 | -6 |
| Wins | 114 | 72 | +42 |
| Losses | 151 | 67 | +84 |
| Win rate | 43.02% | 51.80% | -8.78 pp |
| Profit factor | 0.672 | 0.841 | -0.169 |
| Net PnL | -$37.32 | -$15.07 | -$22.25 |
| Agentic friction | 6.86% | 11.46% | -4.61 pp |

Interpretation:

The initial run generated too many admitted invocations and trades. It also produced too little friction and a worse profit factor than the paper. This indicated that the default admission/risk settings were too permissive for the real-data subset.

Generated local artefacts:

```text
replication/results_real_binance_subset/summary.json
replication/results_real_binance_subset/replication_report.md
replication/results_real_binance_subset/pipeline_log.csv
replication/results_real_binance_subset/trades.csv
replication/results_real_binance_subset/vol_history.csv
replication/results_real_binance_subset/agenticaita_replication.sqlite
```

## Calibration Sweep

A targeted parameter sweep was run to identify settings that better match the paper's aggregate metrics. The repository now includes a dedicated sweep CLI so this can be repeated without running the full report-generation path for every parameter combination.

The full planned grid was initially too slow with the current row-by-row simulator, so a targeted sweep was used. The targeted sweep varied the highest-impact parameters:

| Parameter | Values Tested |
| --- | --- |
| `global_cooldown_seconds` | 2400, 3000, 3600, 4200, 4800, 5400 |
| `z_threshold` | 2.0, 2.25, 2.5 |
| `confidence_gate` | 0.60, 0.65 |
| `absolute_return_floor` | fixed at 0.003 |

Command pattern:

```bash
python replication/sweep.py \
  --config replication/config.yaml \
  --input-csv data/binanceusdm_ohlcv_real_subset/replication_input.csv \
  --out replication/results_calibration_sweep
```

Sweep target metrics:

| Metric | Target |
| --- | ---: |
| Total invocations | 157 |
| Trades executed | 139 |
| Agentic friction | 11.46% |
| Win rate | 51.80% |
| Profit factor | 0.841 |
| Net PnL | -$15.07 |

Top sweep results:

| Rank | Score | Cooldown | Z | Confidence | Invocations | Trades | Friction | Win Rate | Profit Factor | Net PnL |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.641 | 3000 | 2.00 | 0.65 | 169 | 153 | 12.43% | 47.71% | 0.841 | -$9.34 |
| 2 | 1.079 | 3000 | 2.00 | 0.60 | 169 | 163 | 6.51% | 46.63% | 0.839 | -$10.27 |
| 3 | 1.133 | 3600 | 2.25 | 0.65 | 141 | 124 | 14.89% | 46.77% | 0.893 | -$5.24 |
| 4 | 1.456 | 3000 | 2.50 | 0.60 | 167 | 154 | 13.17% | 52.60% | 1.078 | $5.31 |
| 5 | 1.509 | 4200 | 2.50 | 0.60 | 121 | 114 | 8.26% | 49.12% | 0.943 | -$3.07 |

Generated local artefacts:

```text
replication/results_calibration_sweep/calibration_sweep_results.csv
replication/results_calibration_sweep/calibration_sweep_top10.md
```

## Calibrated Defaults

The best sweep result used:

| Parameter | Calibrated Value |
| --- | ---: |
| `igp.global_cooldown_seconds` | 3000 |
| `risk.confidence_gate` | 0.65 |
| `azte.z_threshold` | 2.0 |
| `azte.absolute_return_floor` | 0.003 |

These values were applied to `replication/config.yaml`.

Diff summary:

```diff
igp:
-  global_cooldown_seconds: 1800
+  global_cooldown_seconds: 3000
  per_asset_cooldown_seconds: 300
risk:
-  confidence_gate: 0.60
+  confidence_gate: 0.65
```

The missing runtime dependency `tabulate>=0.9` was also added to `replication/requirements.txt` because `pandas.DataFrame.to_markdown()` requires it during report generation.

## Calibrated Real-Data Run

Command used:

```bash
./.venv/bin/python replication/replicate.py \
  --config replication/config.yaml \
  --input-csv data/binanceusdm_ohlcv_real_subset/replication_input.csv \
  --out replication/results_real_binance_calibrated
```

Results:

| Metric | Calibrated Run | Paper Reported | Delta |
| --- | ---: | ---: | ---: |
| Total invocations | 169 | 157 | +12 |
| Trades executed | 153 | 139 | +14 |
| Risk approved | 153 | 139 | +14 |
| Risk rejected | 16 | 5 | +11 |
| Analyst wait | 5 | 13 | -8 |
| Wins | 73 | 72 | +1 |
| Losses | 80 | 67 | +13 |
| Win rate | 47.71% | 51.80% | -4.09 pp |
| Profit factor | 0.841 | 0.841 | approximately equal |
| Net PnL | -$9.34 | -$15.07 | +$5.73 |
| Agentic friction | 12.43% | 11.46% | +0.96 pp |

Cost sensitivity:

| Scenario | Round-Trip Rate | Total Cost | Adjusted Net PnL |
| --- | ---: | ---: | ---: |
| Zero cost | 0.0000 | $0.00 | -$9.34 |
| Conservative maker only | 0.0004 | $11.51 | -$20.84 |
| Realistic taker plus spread | 0.0010 | $28.76 | -$38.10 |
| Adverse illiquid long tail | 0.0020 | $57.53 | -$66.87 |

Generated local artefacts:

```text
replication/results_real_binance_calibrated/summary.json
replication/results_real_binance_calibrated/replication_report.md
replication/results_real_binance_calibrated/pipeline_log.csv
replication/results_real_binance_calibrated/trades.csv
replication/results_real_binance_calibrated/vol_history.csv
replication/results_real_binance_calibrated/agenticaita_replication.sqlite
```

## What The Results Support

The replication results support the following claims:

| Supported Finding | Evidence |
| --- | --- |
| The published architecture is executable as a dry-run system. | The harness runs end-to-end and writes audit tables, trades, volatility history, summaries, and reports. |
| Admission control is central to matching paper-like counts. | Changing global cooldown from 1800s to 3000s moved invocations from 277 to 169 and trades from 265 to 153. |
| Paper-like friction can be reproduced approximately. | Calibrated friction was 12.43% versus paper 11.46%. |
| Paper-like profit factor can be reproduced approximately. | Calibrated profit factor was 0.8407 versus paper 0.8409. |
| Cost sensitivity behaves as expected. | Increasing round-trip cost monotonically worsened net PnL. |
| The architecture can produce negative, thin-margin trading behavior on real market data. | Calibrated zero-cost PnL was -$9.34; cost-adjusted scenarios were more negative. |

## What The Results Do Not Support

The replication results do not support the following stronger claims:

| Unsupported Claim | Reason |
| --- | --- |
| The original 157 invocations occurred. | Original pipeline logs are unavailable. |
| The original 139 trades occurred. | Original trades table and execution records are unavailable. |
| The 76 original traded assets were reproduced. | This run used a 15-symbol public-data subset. |
| The original live DEX venue was reproduced. | Hyperliquid OHLCV was unavailable for the requested window, and Binance USD-M was used as fallback. |
| Original LLM decisions were reproduced. | The harness uses deterministic proxy Analyst and Risk Manager components. |
| Original order-book-aware execution was reproduced. | Historical L2 snapshots were unavailable. |
| Original stop-loss/take-profit behavior was reproduced. | The current executor uses close-only fixed-horizon exits. |
| Zero human intervention was validated. | Deployment and operational logs are unavailable. |

## Main Technical Findings

### 1. Hyperliquid Was Not Usable For OHLCV Replication

Hyperliquid was the preferred venue because it is closest to the paper's DEX framing. However, the public ccxt query returned no OHLCV candles for the requested paper window. It did return funding rows, but funding alone cannot drive AZTE or the replication pipeline.

This means the practical real-data replication had to use Binance USD-M as a fallback. This is useful for architecture validation but weakens empirical comparability.

### 2. The Initial Harness Was Too Permissive

The original default `global_cooldown_seconds=1800` admitted too many invocations. On the 15-symbol Binance subset, it generated 277 invocations and 265 trades, substantially above the paper's 157 invocations and 139 trades.

This indicates that IGP admission control is not a minor implementation detail. It materially determines the observed trade count and friction profile.

### 3. Calibration Improved Aggregate Alignment

Changing only two defaults produced much closer aggregate behavior:

```yaml
igp:
  global_cooldown_seconds: 3000
risk:
  confidence_gate: 0.65
```

This brought the run close to the paper on invocations, trades, friction, and profit factor.

### 4. The Remaining Gap Is Execution Semantics

After calibration, counts and friction were close, but win rate and net PnL still differed. The most likely reason is that the original calibrated run used close-only fixed-horizon exits, while the paper reports stop-loss and take-profit behavior.

Close-only fallback behavior:

```text
entry = current close
exit = close after fixed horizon
```

More paper-aligned OHLCV behavior uses:

```text
entry = current close
stop loss = derived from Analyst/Risk Manager output
take profit = derived from Analyst/Risk Manager output
exit = first intrabar OHLC hit, or timeout
```

This requires loading full OHLCV rather than only `timestamp,asset,close`.

## Limitations

The main limitations are structural rather than incidental:

| Limitation | Impact |
| --- | --- |
| Public fallback venue | Binance USD-M is not the paper's original DEX venue. |
| Limited asset universe | 15 symbols is smaller than 117 monitored assets and 76 traded assets. |
| Missing original logs | Cannot validate original invocation/trade sequence. |
| Missing prompts and LLM calls | Cannot reproduce Analyst or Risk Manager decisions. |
| Missing L2 snapshots | Cannot reproduce order-book-aware reasoning. |
| Close-only input | Cannot simulate stop-loss/take-profit hits accurately. |
| Fixed-horizon exits | May distort win rate, profit factor, and PnL. |
| Parameter calibration | Improves aggregate fit but is not proof of empirical reproduction. |

## Verification

Replication tests were run after the dependency and config updates:

```bash
./.venv/bin/python -m pytest -q replication
```

Result:

```text
4 passed
```

## Final Conclusion

The replication work successfully demonstrates a functional Paper2Code-style architecture replication of AGENTICAITA. The harness can ingest public market data, run an auditable AZTE/CBD/agent/risk/execution pipeline, write replication artefacts, and produce aggregate metrics that become reasonably paper-like after calibration.

The strongest aligned metrics after calibration are:

| Metric | Calibrated | Paper |
| --- | ---: | ---: |
| Invocations | 169 | 157 |
| Trades | 153 | 139 |
| Friction | 12.43% | 11.46% |
| Profit factor | 0.841 | 0.841 |

The weakest aligned metrics are:

| Metric | Calibrated | Paper |
| --- | ---: | ---: |
| Win rate | 47.71% | 51.80% |
| Net PnL | -$9.34 | -$15.07 |

The appropriate conclusion is moderate functional alignment but low empirical proof. The architecture is plausible and executable, and the aggregate behavior can be made similar on real public market data. However, the paper's original live-session claims remain unsupported without original artefacts.

## Recommended Next Work

The next highest-value work is to improve execution realism rather than continue tuning aggregate parameters.

Recommended order:

1. Extend replication input loading from `timestamp,asset,close` to full `timestamp,asset,open,high,low,close,volume`.
2. Replace fixed-horizon exits with stop-loss/take-profit/timeout execution over OHLC bars.
3. Run a larger all-active-symbol Binance or Bybit fallback universe to test whether counts remain stable outside the 15-symbol subset.
4. If Hyperliquid OHLCV becomes available, rerun the calibrated harness on the preferred venue.
5. Keep the report language explicit: these runs are functional architecture replications, not empirical reproductions of the original five-day dry-run.
