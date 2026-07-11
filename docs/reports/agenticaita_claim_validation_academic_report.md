# Academic Report: Paper2Code Validation of AGENTICAITA Claims

**Date:** 2026-07-10  
**Repository:** `agenticaita_paper2code_validation`  
**Target paper:** AGENTICAITA, arXiv `2605.12532v1`  
**Validation mode:** Paper2Code static claim audit with complementary functional replication pathway

## Abstract

This report documents the purpose, methodology, findings, and limitations of a Paper2Code validation project for the AGENTICAITA paper. The project set out to determine which of the paper's quantitative and methodological claims can be independently checked from the information reported in the paper, which claims are internally consistent, and which claims remain unverifiable without unreleased experimental artefacts. The validation implementation evaluates 43 claims spanning pipeline counts, trading performance, statistical significance, transaction-cost sensitivity, AZTE trigger properties, CBD diversification properties, asset-class aggregation, and raw-data-dependent assertions. The static validation run produced 35 passing claims, 2 qualified claims, 0 failing claims, and 6 unsupported claims. These results indicate that the paper's reported numerical quantities are internally consistent wherever they are computable from the published text, while important claims about live operation, autonomy, provenance, funding-corrected benchmarking, and empirical CBD-trade relationships cannot be independently verified without the authors' original logs, SQLite database, configuration history, and market-data artefacts.

## 1. Project Objective

The project was designed as a reproducibility and auditability exercise rather than as a claim that the original AGENTICAITA live dry-run can be reconstructed exactly. Its central objective was to convert paper-level claims into executable checks. In practical terms, the project asks the following questions:

1. Are the numerical values reported in the paper internally consistent with one another?
2. Are derived quantities such as rates, PnL, profit factor, win rate, benchmark alpha, cost sensitivity, and statistical significance reproducible from the reported numbers?
3. Which claims require external artefacts that are absent from the paper?
4. Can a separate executable replication harness approximate the published architecture closely enough to generate comparable audit artefacts for new runs?

The repository therefore contains two complementary paths:

| Path | Purpose | What It Can Establish | What It Cannot Establish |
| --- | --- | --- | --- |
| `validation/` | Static Paper2Code claim audit | Internal consistency of reported quantities and clear classification of unsupported claims | Original live decisions, hidden logs, raw SQLite provenance, or exact execution path |
| `replication/` | Functional architecture replication | An auditable approximation of the published architecture, including AZTE, CBD, Analyst, Risk Manager, Executor, cooldowns, risk gates, and output artefacts | Proof that the original five-day dry-run occurred exactly as described |

This distinction is central to the interpretation of the findings. The validation module evaluates claims that can be recomputed from reported quantities. The replication module provides a runnable system that resembles the architecture, but it is not evidence for the original experiment unless the original artefacts are available.

## 2. Scope of Validation

The validation module explicitly avoids overclaiming. It does not attempt to recreate the live trading system because the paper does not provide the original exchange fills, L2 order book snapshots, LLM call logs, prompts, system telemetry, raw SQLite database, funding-rate cash-flow records, or production configuration history.

Instead, the module validates reproducible paper-level quantities, including:

| Claim Area | Examples of Checked Quantities |
| --- | --- |
| Pipeline counts | Total invocations, long/short/wait rates, Risk Manager approval and rejection rates, trade execution rate, conservation of counts |
| Trading performance | Win rate, net PnL, return on notional, profit factor, mean win, mean loss, risk/reward ratio, break-even win rate |
| Benchmark comparison | BTC buy-and-hold loss, dollar alpha, percentage-point alpha |
| Statistical inference | Normal-approximation p-value, exact binomial p-value, significance conclusion |
| Transaction costs | Four paper-reported cost scenarios derived from total notional and assumed round-trip rates |
| AZTE | False-positive-rate interpretation and warmup-window arithmetic |
| CBD | Bounded anomaly transform and diversification-score monotonicity |
| Asset-class table | Trade-count sum, net-PnL sum, weighted win rate, weighted confidence |
| Unsupported raw claims | Autonomy, no post-processing, live conditions, no tuning, funding-corrected benchmark, empirical CBD-PnL relationships |

## 3. Methodology

### 3.1 Claim Extraction and Encoding

The project encodes reported paper quantities in `validation/claims.py` as immutable data structures. This separation is deliberate: the reported values are stored as data, while the calculations used to audit them are implemented separately in `validation/metrics.py`. This design improves reviewability because readers can inspect the source values independently from the formulas used to validate them.

The principal reported quantities are:

| Quantity | Reported Value |
| --- | ---: |
| Total invocations | 157 |
| Analyst long signals | 142 |
| Analyst short signals | 2 |
| Analyst wait signals | 13 |
| Risk Manager approvals | 139 |
| Risk Manager rejections | 5 |
| Trades executed | 139 |
| Unique assets | 76 |
| Wins | 72 |
| Losses | 67 |
| Gross profit | $79.67 |
| Gross loss | $94.74 |
| Net PnL | -$15.07 |
| Total notional | $26,079 |
| BTC buy-and-hold PnL | -$3,912 |
| Reported alpha | $3,896 |
| Mean stop-loss percentage | 0.627% |
| Mean take-profit percentage | 1.894% |

### 3.2 Validation Tolerances

The validation configuration defines explicit tolerances to distinguish material discrepancies from ordinary rounding differences in tables and prose. The principal tolerances are:

| Tolerance Type | Value |
| --- | ---: |
| Money tolerance | $0.03 |
| Percentage-point tolerance | 0.06 percentage points |
| Ratio tolerance | 0.005 |
| P-value tolerance | 0.04 |

Some individual checks use more specific tolerances, such as exact integer equality for conservation identities, $0.01 for net PnL arithmetic, or $1.00 for alpha because the paper's benchmark and table values are rounded.

### 3.3 Status Classification

Each claim receives one of four statuses:

| Status | Meaning |
| --- | --- |
| `pass` | The computed value matches the paper value within the stated tolerance, or the stated property holds. |
| `qualified` | The claim is numerically reproducible only under a particular interpretation, or the paper wording is methodologically ambiguous. |
| `fail` | The computed value contradicts the paper value beyond tolerance. |
| `unsupported` | The claim cannot be independently evaluated from the paper alone and requires missing raw data, logs, or configuration artefacts. |

### 3.4 Reproducible Command

The static validation results in this report were regenerated with:

```bash
cd validation
python validate_claims.py --out results
```

The run completed successfully and produced:

```text
Validation complete
pass: 35
qualified: 2
fail: 0
unsupported: 6
Report: results/validation_report.md
```

## 4. Results Overview

The static validation run evaluated 43 total claims.

| Status | Count | Share |
| --- | ---: | ---: |
| Pass | 35 | 81.4% |
| Qualified | 2 | 4.7% |
| Fail | 0 | 0.0% |
| Unsupported | 6 | 14.0% |
| Total | 43 | 100.0% |

The headline result is that no computable paper claim failed validation. The paper's reported numerical quantities are internally consistent under the implemented audit checks. The two qualified claims concern methodological interpretation rather than direct arithmetic contradiction. The six unsupported claims are claims that require artefacts not included in the paper.

## 5. Detailed Findings

### 5.1 Pipeline Claims

All 11 pipeline claims passed. These checks validate whether the paper's reported pipeline counts and rates are mutually consistent.

| Claim | Paper Value | Computed Value | Status |
| --- | ---: | ---: | --- |
| Long signal rate | 90.4% | 90.44586% | Pass |
| Short signal rate | 1.3% | 1.273885% | Pass |
| Wait signal rate | 8.3% | 8.280255% | Pass |
| Risk Manager approval rate | 96.5% | 96.527778% | Pass |
| Risk Manager rejection rate, RM denominator | 3.5% | 3.472222% | Pass |
| Risk Manager rejection rate, all invocations | 3.2% | 3.184713% | Pass |
| Trade execution rate | 88.5% | 88.535032% | Pass |
| Asset breadth | 54.68% | 54.676259% | Pass |
| Agentic friction | 11.5% | 11.464968% | Pass |
| Analyst signal conservation | 157 | 157 | Pass |
| Risk Manager count conservation | 144 | 144 | Pass |

These results show that the pipeline table is arithmetically coherent. The signal counts sum correctly: 142 long + 2 short + 13 wait = 157 total invocations. Similarly, the Risk Manager counts sum correctly: 139 approved + 5 rejected = 144 invocations reaching the Risk Manager. The reported agentic friction is also reproducible as `(5 rejected + 13 wait) / 157 = 11.464968%`.

The practical interpretation is that there is no evidence of count inconsistency in the paper's pipeline description. However, these checks validate only internal consistency. They do not prove that the invocations occurred, that the agent was autonomous, or that the routing decisions came from the claimed live system.

### 5.2 Trading Performance Claims

All 11 trading-performance claims passed. These claims examine the relationship among wins, losses, PnL, total notional, profit factor, risk/reward, and benchmark alpha.

| Claim | Paper Value | Computed Value | Status |
| --- | ---: | ---: | --- |
| Win rate | 51.80% | 51.798561% | Pass |
| Net PnL | -$15.07 | -$15.07 | Pass |
| Return on notional | -0.058% | -0.057786% | Pass |
| Profit factor | 0.841 | 0.840933 | Pass |
| Mean win | $1.11 | $1.106528 | Pass |
| Mean loss | $1.41 | $1.414030 | Pass |
| Risk/reward ratio | 3.02 | 3.020734 | Pass |
| Break-even win rate | 24.9% | 24.875622% | Pass |
| BTC benchmark loss | -$3,912 | -$3,911.85 | Pass |
| Dollar alpha | $3,896 | $3,896.93 | Pass |
| Percentage-point alpha | 14.94 pp | 14.942214 pp | Pass |

These checks show that the paper's economic summary is internally consistent. The agent lost a small amount in absolute terms, with net PnL of -$15.07 on $26,079 notional, corresponding to a return of approximately -0.058%. The BTC benchmark, represented as a -15% price-only loss on the same notional base, gives approximately -$3,911.85. Therefore, the reported dollar alpha is reproducible as:

```text
AGENTICAITA PnL - BTC PnL = -15.07 - (-3912.00) = 3896.93
```

The validation therefore supports the paper's narrower claim that the reported run lost money in absolute terms while outperforming a strongly declining BTC benchmark in price-only arithmetic. It does not independently validate a funding-adjusted perpetual benchmark, because that requires timestamped funding cash flows and position sizing.

### 5.3 Statistical Claims

The statistical checks produced 2 passes and 1 qualified result.

| Claim | Paper Value | Computed Value | Status |
| --- | --- | ---: | --- |
| Normal-approximation p-value | approximately 0.34 | 0.335748 | Pass |
| Exact one-sided binomial p-value | approximately 0.34 | 0.367270 | Qualified |
| Significance conclusion | not significant | one-sided 0.367270; two-sided 0.734539 | Pass |

The paper's p-value of approximately 0.34 is reproducible as a one-sided normal approximation for 72 wins out of 139 trades against a 50% null win rate. However, the exact one-sided binomial test gives approximately 0.367, and the exact two-sided binomial test gives approximately 0.735.

This does not undermine the paper's substantive statistical conclusion. Under either approximation or exact testing, the observed 51.80% win rate is not statistically significant relative to a 50% null. The qualification concerns the method used to obtain the reported p-value, not the conclusion that the result is statistically indistinguishable from random at conventional thresholds.

### 5.4 Transaction-Cost Sensitivity Claims

All 4 transaction-cost sensitivity claims passed. The validation recomputed each cost scenario from total notional multiplied by the scenario's round-trip cost rate.

| Scenario | Rate | Paper Cost | Computed Cost | Paper Adjusted PnL | Computed Adjusted PnL | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Zero cost | 0.0000 | $0.00 | $0.00 | -$15.07 | -$15.07 | Pass |
| Conservative maker only | 0.0004 | $10.43 | $10.4316 | -$25.50 | -$25.5016 | Pass |
| Realistic taker plus spread | 0.0010 | $26.09 | $26.0790 | -$41.16 | -$41.1490 | Pass |
| Adverse illiquid long tail | 0.0020 | $52.18 | $52.1580 | -$67.25 | -$67.2280 | Pass |

The results show that the paper's cost-sensitivity table is arithmetically consistent within cents-level rounding. The appropriate interpretation is limited: these checks validate table arithmetic, not live execution quality. Since the reported paper run was a dry-run without real order placement, the cost scenarios are modeled sensitivities rather than measured slippage or exchange-fee outcomes.

### 5.5 AZTE Claims

The AZTE checks produced 1 pass and 1 qualified result.

| Claim | Paper Value | Computed Value | Status |
| --- | --- | --- | --- |
| 2-sigma false-positive rate | approximately 4.6% | one-sided 2.275013%; two-sided 4.550026% | Qualified |
| Warmup window | 30 minutes | 30 minutes | Pass |

The warmup arithmetic is exact: a rolling window of 30 observations at 60-second intervals gives a 30-minute warmup period.

The false-positive-rate claim is methodologically ambiguous. A two-sided standard-normal tail beyond absolute value 2 is approximately 4.55%, matching the paper's approximately 4.6% statement. However, the paper's trigger is written as `z_t >= 2.0`, which is one-sided and has a standard-normal tail probability of approximately 2.28%. Additionally, the trigger is based on an absolute-return construction, so a direct normal-tail interpretation requires more distributional justification. This is a qualified claim rather than a failure because the paper's number is correct under the two-sided normal-tail interpretation.

### 5.6 CBD Claims

Both CBD property checks passed.

| Claim | Result | Status |
| --- | --- | --- |
| Saturated anomaly transform remains bounded in `[0, 1)` | Holds over representative values and analytical form | Pass |
| Higher decorrelation increases CBD score for identical anomaly magnitude | `rho_cb=0.9` score exceeds `rho_cb=0.1` score | Pass |

The validation confirms that the CBD formulation behaves as described at the formula level. For example, with anomaly magnitude fixed at `z=3.0`, the score for `rho_cb=0.9` is 0.646735, while the score for `rho_cb=0.1` is 0.246735. This demonstrates that, all else equal, higher decorrelation from the benchmark increases the CBD score.

These are mathematical property checks. They do not validate the empirical claim that specific high- or low-CBD assets were responsible for the paper's observed trade outcomes, because that requires per-asset price series, CBD scores, and trade-level PnL records.

### 5.7 Asset-Class Table Claims

All 4 asset-class aggregation claims passed.

| Claim | Paper Value | Computed Value | Status |
| --- | ---: | ---: | --- |
| Trade-count sum | 139 | 139 | Pass |
| Net-PnL sum | -$15.07 | -$15.08 | Pass |
| Weighted win rate | 51.80% | 51.80% | Pass |
| Weighted confidence | 0.755 | 0.754223 | Pass |

The one-cent difference in net-PnL aggregation is consistent with rounded asset-class rows. The weighted win-rate and confidence calculations also agree within reasonable rounding tolerance. These results support the internal consistency of the asset-class summary table.

### 5.8 Unsupported Claims

Six claims were classified as unsupported because they are not computable from the paper text alone.

| Claim | Reason Unsupported |
| --- | --- |
| 157 autonomous invocations with zero human interventions | Requires system logs or an experiment audit trail. |
| Figures and metrics extracted directly from SQLite with no post-processing | Requires the SQLite database and plotting scripts. |
| Funding-corrected BTC perpetual benchmark is worse than price-only BTC benchmark | Requires timestamped funding-rate cash flows and position sizing. |
| Top performers had high `rho_cb`, while low-`rho_cb` assets produced deepest losses | Requires per-asset price series, CBD scores, and trade-level PnL records. |
| The five-day dry run used live market conditions and qwen3.5:9b via remote Ollama | Requires telemetry, API logs, and environment configuration. |
| No parameters were tuned during the session | Requires configuration history and deployment logs. |

These unsupported classifications are not negative findings about the paper's truthfulness. They are statements about evidentiary availability. Without the relevant artefacts, an independent validator cannot distinguish between a true operational claim and a merely reported operational claim.

## 6. Interpretation of Findings

The validation results support three main conclusions.

First, the paper's reported numerical tables are internally coherent. Counts conserve, percentages recompute correctly, PnL arithmetic is consistent, transaction-cost scenarios match the stated notional and rates, and benchmark alpha is reproducible from the reported quantities.

Second, the paper's own caution about statistical strength is supported. The observed win rate of 72 wins in 139 trades is not statistically significant versus a 50% null. The exact p-value differs from the paper's approximate p-value, but both approaches lead to the same substantive conclusion.

Third, the strongest operational claims remain outside the evidentiary reach of the published paper. The project can validate arithmetic and formula-level consistency. It cannot independently validate autonomy, live execution conditions, absence of tuning, direct SQLite provenance, original LLM decisions, or funding-adjusted benchmark accounting without primary artefacts.

## 7. What the Claims Show

The claim audit shows that AGENTICAITA's reported run is best understood as an internally consistent but externally underdetermined experimental report.

The internal consistency is strong. The reported pipeline, performance, cost, benchmark, and table quantities fit together with no detected arithmetic failures. This reduces the likelihood of simple spreadsheet errors, inconsistent denominators, or obvious PnL manipulation in the reported aggregates.

The statistical evidence is weak by design and by result. The run lost money in absolute terms, had a small positive deviation from 50% win rate, and did not establish statistically significant trading skill. Its most favorable reported outcome is relative benchmark performance during a period when BTC declined sharply. That alpha calculation is arithmetically correct under the price-only benchmark interpretation, but it is not equivalent to proving robust strategy profitability.

The missing artefacts materially limit reproducibility. A full independent replication of the original run would require the raw decision log, market snapshots, LLM inputs and outputs, risk-manager records, execution simulator state, funding-rate accounting, and configuration history. The absence of those artefacts means that several important claims can only be treated as reported assertions, not independently verified facts.

## 8. Relationship to Functional Replication

The repository's replication harness addresses a different but related question: whether the published architecture can be approximated as executable software. It includes the main architectural concepts described in the paper: AZTE event detection, CBD scoring, a sequential Analyst-to-Risk-Manager-to-Executor pipeline, deterministic or LLM-backed agent modes, risk hard gates, cooldown logic, audit outputs, and transaction-cost sensitivity.

The replication configuration records representative defaults, including:

| Component | Configuration |
| --- | --- |
| AZTE polling interval | 60 seconds |
| AZTE rolling window | 30 observations |
| AZTE z-threshold | 2.0 |
| Absolute-return floor | 0.003 |
| Risk confidence gate | 0.65 |
| Maximum stop-loss fraction | 0.02 |
| Base position size | $188 |
| Maximum position size | $500 |
| CBD alpha | 0.5 |
| CBD kappa | 0.5 |
| Benchmark asset | BTC |
| LLM provider path | OpenRouter-compatible, with deterministic fallback paths elsewhere in the repository |

This replication path is valuable for engineering reproducibility because it can generate new audit artefacts under controlled conditions. However, it should not be confused with verification of the original run. New replication outputs are comparable artefacts, not proof of historical equivalence.

## 9. Public Market-Data Reconstruction Limits

The repository also supports public market-data reconstruction workflows, including OHLCV downloaders, funding-rate storage where available, AZTE/CBD metric computation, and real-data validation adapters. These workflows can test public data coverage and compute deterministic metrics from recovered candles.

However, public APIs cannot recover several classes of historical state that matter for exact replication:

| Can Be Reconstructed from Public APIs | Cannot Be Reconstructed from Public APIs |
| --- | --- |
| OHLCV candles, where the venue exposes historical candles | Original L2 order book snapshots used by the agent |
| Funding-rate availability, where the venue exposes funding history | Original LLM prompts, completions, and deliberation records |
| Deterministic AZTE/CBD metrics from recovered candles | Original Risk Manager approvals and rejections |
| Coverage reports and data-quality checks | Original SQLite dry-run database and plotting provenance |

The repository documentation notes that a historical Hyperliquid reconstruction attempt for 15 symbols in the paper window returned funding rows but no OHLCV candles for the requested symbols through that pathway. Binance USD-M futures can be used as a CCXT-compatible fallback for comparable public-market-condition checks, but fallback venue data is not evidence for the paper's exact Hyperliquid session.

## 10. Limitations

This report has several limitations.

First, the validation relies on the paper-reported aggregate values. It can detect internal inconsistency among reported numbers, but it cannot verify whether the reported aggregates were derived from the claimed raw source without access to that source.

Second, the tests are claim-driven rather than exhaustive. They cover the claims encoded in the repository, not every possible statement in the paper.

Third, some tolerances necessarily reflect judgment about rounding. The repository makes these tolerances explicit, but alternative validators could choose stricter or looser thresholds.

Fourth, the static validation does not measure trading strategy robustness. It evaluates reported arithmetic and formula-level claims, not out-of-sample profitability.

Fifth, the replication harness is an approximation. It helps operationalize the paper's architecture, but it cannot reconstruct the original hidden state or prove historical identity with the paper's run.

## 11. Recommendations for Stronger Reproducibility

The AGENTICAITA paper would become substantially more independently verifiable if the following artefacts were released:

1. The original SQLite database used for figures and metrics.
2. A schema description and plotting scripts for all reported tables and figures.
3. Timestamped LLM prompts, completions, model identifiers, and inference parameters.
4. Analyst and Risk Manager decision logs, including rejected and wait decisions.
5. Market-data snapshots or exact historical data references used by the system.
6. Funding-rate time series and benchmark position-sizing assumptions.
7. Configuration files and version history proving no mid-run parameter tuning.
8. A replay script capable of regenerating reported aggregates from raw artefacts.

These artefacts would allow the unsupported claims to move from assertion-level evidence to independently reproducible evidence.

## 12. Conclusion

The Paper2Code validation project achieved its primary objective: it translated the AGENTICAITA paper's reported numerical claims into executable checks and classified the evidentiary status of each claim. The resulting audit found 35 passing claims, 2 qualified claims, no failing claims, and 6 unsupported claims.

The strongest conclusion is that the paper's reported aggregate numbers are internally consistent. There is no detected arithmetic contradiction in the pipeline counts, trading metrics, benchmark alpha, transaction-cost table, CBD formula properties, or asset-class aggregation. The statistical conclusion that the observed win rate is not significant is also supported.

The equally important limitation is that internal consistency is not full reproducibility. Claims about live autonomy, raw SQLite provenance, absence of human intervention, absence of tuning, funding-corrected benchmarking, and empirical CBD-trade relationships remain unverifiable without primary artefacts. The project therefore provides a clear boundary between what the paper establishes numerically from its own reported quantities and what remains dependent on unreleased experimental evidence.

## Appendix A: Static Validation Summary

| Category | Claims | Pass | Qualified | Fail | Unsupported |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pipeline counts | 11 | 11 | 0 | 0 | 0 |
| Trading metrics | 11 | 11 | 0 | 0 | 0 |
| Statistical checks | 3 | 2 | 1 | 0 | 0 |
| Transaction costs | 4 | 4 | 0 | 0 | 0 |
| AZTE properties | 2 | 1 | 1 | 0 | 0 |
| CBD properties | 2 | 2 | 0 | 0 | 0 |
| Asset-class table | 4 | 4 | 0 | 0 | 0 |
| Raw-data-dependent claims | 6 | 0 | 0 | 0 | 6 |
| **Total** | **43** | **35** | **2** | **0** | **6** |

## Appendix B: Reproducibility Notes

The source validation report is generated locally under `validation/results/`, which is intentionally ignored by git as a generated artefact. This academic report is saved under `docs/reports/` as a compact, reviewer-facing summary derived from reproducible commands.

The principal generated files from the static validation command are:

| File | Purpose |
| --- | --- |
| `validation/results/validation_report.md` | Human-readable generated validation report |
| `validation/results/validation_results.json` | Structured claim results |
| `validation/results/validation_results.csv` | Tabular claim results |

The validation command can be rerun at any time with:

```bash
cd validation
python validate_claims.py --out results
```
