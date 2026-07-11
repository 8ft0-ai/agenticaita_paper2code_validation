# Concluding Assessment of the AGENTICAITA Paper

Date: 2026-07-11

## Summary

The repository evidence supports a narrow conclusion: the AGENTICAITA paper's published aggregate numbers are mostly internally consistent, but the claimed live experiment is not independently reproducible from the paper alone. Functional replication runs over reconstructed public market data do not recover the paper's reported agent behavior, trade distribution, performance, or benchmark alpha.

This does not prove that the paper's reported dry-run did not occur. It does show that the paper is empirically under-documented for independent verification.

## What the Validation Supports

The static Paper2Code audit found that the paper's reported numerical claims are largely coherent where they can be recomputed from published values. Counts, rate calculations, PnL relationships, transaction-cost sensitivity arithmetic, and several derived performance quantities are reproducible from the text.

This supports the paper's internal arithmetic consistency. It does not validate the original live system, the original agent decisions, or the original market-data provenance.

## What Remains Unsupported

Several important claims require artefacts that are not included in the paper:

| Claim Area | Missing Evidence |
| --- | --- |
| Live operation | Original runtime logs, telemetry, exchange state, and dry-run records |
| Zero human intervention | Audit trail proving no manual selection, override, tuning, or post-processing |
| Raw SQLite provenance | The original SQLite database and schema-level provenance |
| LLM decision path | Original prompts, completions, model versions, provider settings, and retry/fallback records |
| Risk Manager decisions | Original approval/rejection decisions and negotiation traces |
| Funding-aware benchmark | Funding cash-flow records and exact benchmark construction |
| Market microstructure context | Original L2 order book snapshots and execution-time market state |

Without these artefacts, the strongest reproducible result is a paper-level consistency audit, not an empirical reproduction of the reported experiment.

## Public-Data Replication Results

The large-universe functional replication reconstructed a Binance USD-M proxy dataset for the paper window:

| Field | Value |
| --- | ---: |
| Source symbols selected | 76 |
| Distinct normalized assets | 69 |
| One-minute candles | 656640 |
| Window | 2026-04-06 to 2026-04-11 |

This dataset can exercise the repository's functional architecture, but it is not the authors' original market state. Public OHLCV data cannot recover the original L2 order books, LLM prompts, LLM completions, Risk Manager decisions, SQLite logs, or funding-adjusted execution history.

## Deterministic Functional Replication

The deterministic run reproduced some structural throughput but not the paper's behavior or performance.

| Metric | Paper | Deterministic Run |
| --- | ---: | ---: |
| Total invocations | 157 | 173 |
| Analyst long | 142 | 72 |
| Analyst short | 2 | 86 |
| Analyst wait | 13 | 15 |
| Risk approved | 139 | 139 |
| Trades executed | 139 | 139 |
| Unique traded assets | 76 | 32 |
| Wins | 72 | 48 |
| Losses | 67 | 91 |
| Net PnL USD | -15.07 | -34.725153204272694 |
| Win rate percent | 51.8 | 34.53237410071942 |
| Profit factor | 0.841 | 0.5658311128336146 |
| BTC benchmark alpha USD | 3896.0 | -1513.52 |

The deterministic proxy matched the paper's `139` Risk Manager approvals and `139` executed trades, but the match is structural rather than empirical. Signal mix, unique traded assets, win/loss distribution, PnL, win rate, profit factor, and BTC benchmark alpha were divergent.

## LLM-Backed Functional Replication

The OpenRouter-backed LLM run used `qwen/qwen-2.5-7b-instruct` against the same public dataset. It confirmed that the LLM path can run end-to-end, but its behavior diverged even more from the paper's reported agent behavior.

| Metric | Paper | LLM Run |
| --- | ---: | ---: |
| Total invocations | 157 | 173 |
| Analyst long | 142 | 16 |
| Analyst short | 2 | 66 |
| Analyst wait | 13 | 91 |
| Risk approved | 139 | 11 |
| Risk rejected | 5 | 162 |
| Trades executed | 139 | 11 |
| Unique traded assets | 76 | 10 |
| Wins | 72 | 2 |
| Losses | 67 | 9 |
| Net PnL USD | -15.07 | -7.981283722911384 |
| Win rate percent | 51.8 | 18.181818181818183 |
| Profit factor | 0.841 | 0.1076409316333886 |
| BTC benchmark alpha USD | 3896.0 | -125.01 |

The LLM run was much more conservative than both the deterministic proxy and the paper's reported long-heavy signal profile. It produced the same number of AZTE invocations as the deterministic run, but only `11` executed trades.

The LLM audit log recorded:

| Usage Metric | Value |
| --- | ---: |
| Audit rows | 184 |
| Prompt tokens | 126404 |
| Completion tokens | 30853 |
| Total tokens | 157257 |
| Reported OpenRouter cost USD | 0.0139344 |

The run also emitted 17 Analyst fallback warnings because some live LLM responses did not include required actionable entry fields. These fallbacks are documented in the run output and reinforce that exact agent behavior depends on prompt design, model behavior, schema adherence, and fallback policy.

## Interpretation

The combined evidence points to four conclusions:

1. The paper is arithmetically coherent where its claims are checkable from published aggregate values.
2. The original empirical run is not independently reproducible without unreleased artefacts.
3. A functional implementation of the described architecture can be built and exercised over public data, but it does not recover the paper's reported behavior or outcome metrics.
4. The reported LLM behavior appears highly dependent on unavailable prompts, completions, model/provider conditions, risk decisions, market state, and configuration history.

The functional replication therefore neither falsifies nor validates the reported live dry-run. It demonstrates that the architecture can be approximated and audited, while also showing that the paper's headline empirical claims require substantially more provenance to be independently verified.

## Final Assessment

The AGENTICAITA paper should be treated as internally consistent but empirically under-documented.

Its numerical tables and aggregate relationships are mostly reproducible from the text. However, the live-agent claims, autonomy claims, raw-data provenance claims, funding-adjusted benchmark claims, and LLM decision claims remain unverified. Public-data deterministic and LLM-backed replications produce divergent behavior and do not recover the paper's reported positive benchmark alpha.

Independent validation would require the authors to release the original SQLite database, prompt and completion logs, model/provider configuration, Risk Manager traces, execution-time market snapshots, funding records, and exact benchmark-construction code.
