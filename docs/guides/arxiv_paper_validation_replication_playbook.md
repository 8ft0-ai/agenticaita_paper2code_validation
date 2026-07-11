# arXiv Paper Validation and Replication Playbook

Date: 2026-07-11

Start with [Paper Validation Guides — Start Here](README.md). This playbook is the methodological reference. Repository commands, contribution rules, credentials, and generated-output exclusions belong in the generated `PROJECT_PROFILE.md`.

## Purpose and standard

The goal is to make a defensible statement about what can and cannot be independently verified. Do not treat similarity to a reported metric as reproduction.

> Separate claim validation, artefact audit, public-data reconstruction, functional implementation, and empirical rerun. Missing artefacts, unavailable historical data, malformed model output, and contradictory benchmarks are first-class findings.

A project succeeds when it makes the evidence boundary clearer, including when the conclusion is `not independently reproducible from available materials`.

## Local terminology

| Term | Meaning |
| --- | --- |
| Static validation | Recomputing claims from paper text, tables, equations, appendices, or released static files. |
| Direct reproduction | Rerunning the original released code, data, evaluation path, and materially equivalent runtime context. |
| Independent replication | Independently implementing the method using equivalent inputs and evaluation, with differences disclosed. |
| Proxy replication | Substituting material data, model, provider, benchmark, or runtime elements. |
| Functional replication | Implementing and exercising the described architecture without claiming empirical equivalence. |
| Synthetic replication | Exercising mechanics under controlled artificial inputs. |
| Diagnostic validation | Testing one bounded claim, formula, component, or failure mode. |
| Negative finding | Evidence that a path is unavailable, unsupported, stale, ambiguous, contradictory, or not worth continuing. |

Use the [claim language guide](reproduction_claim_language.md) in reports.

## Phase 0 — freeze scope and paper version

Record:

- title, arXiv ID, exact version, URL, authors, and date accessed;
- paper type: empirical, theoretical, benchmark, simulation, system/demo, or mixed;
- headline task and conclusions;
- claims of live operation, autonomy, proprietary data, private logs, closed models, or manual intervention;
- expected project classification;
- what evidence could materially change the final conclusion.

Freeze each milestone against one paper version. When a later version changes a material claim, add a version-diff record rather than silently replacing the ledger.

### Gate A — scope and artefacts

Decide:

1. Is direct reproduction possible from available artefacts?
2. Which claims are important enough to justify further work?
3. What missing artefact stops or downgrades each path?
4. Is functional, proxy, or diagnostic work still valuable?

Record the decision and consequence.

## Phase 1 — artefact, legal, and retention audit

Inventory paper source, code, raw and processed data, splits, runtime logs, checkpoints, prompts, completions, model versions, environment, evaluation code, and benchmark construction.

For each artefact record:

- availability and location;
- claim IDs that depend on it;
- reproduction impact;
- licence, API terms, redistribution, and retention constraints;
- owner and expiry for externally retained evidence;
- whether personal, sensitive, or jurisdictionally restricted data is present.

### Focused author request

Request only artefacts material to prioritised claims. Include exact inputs and filters, transformations, splits and seeds, runtime configuration, logs and interventions, model/prompt/provider details, evaluation code, dependency/container information, and benchmark logic.

### Gate B — data and legal adequacy

Before bulk acquisition, confirm:

- exact historical window, entities, granularity, schema, and coverage;
- licence and intended-use compatibility;
- redistribution and sample-commit rights;
- retention, rate limits, and scraping restrictions;
- privacy and sensitive-data constraints.

A materially different source is a proxy. A documented retention limit that excludes the paper window is a negative finding and a stop condition for that recovery path.

## Phase 2 — prioritised claim ledger

Create stable IDs and include at least:

| Field | Purpose |
| --- | --- |
| `paper_version` | Version against which the claim was extracted. |
| `location` | Page, section, table, figure, equation, or appendix. |
| `claim_type` | Quantitative, benchmark, dataset, method, autonomy, cost, robustness, or qualitative. |
| `claim_importance` | `headline`, `supporting`, or `contextual`. |
| `validation_priority` | `critical`, `useful`, or `optional`. |
| `claim_text` and `reported_value` | Exact or near-exact assertion. |
| `dependencies` | Required data, code, logs, model, benchmark, or assumptions. |
| `validation_method` | Arithmetic, statistical, rerun, public-data check, or manual review. |
| `extraction_method` and `extraction_confidence` | How reliably the value was obtained. |
| `manually_verified` | Whether a material extraction was checked against the source. |
| `status` and `status_rationale` | Supported, partially supported, unsupported, contradicted, not testable, unresolved. |
| `evidence_refs` | Tests, reports, manifests, files, or external sources. |

Validate critical headline claims first. Exhaustive checking of contextual statistics is optional when the central conclusion is already bounded.

### Status rules

- `supported`: independently recomputed or observed from available evidence;
- `partially_supported`: a narrower claim is supported;
- `unsupported`: required artefacts or definitions are absent;
- `contradicted`: available evidence conflicts with the claim or another statement;
- `not_testable`: the assertion cannot be operationalised;
- `unresolved`: a material ambiguity remains pending clarification.

Status is separate from extraction confidence.

## Phase 3 — validation plan

Implement cheap, deterministic checks before a full model or system build.

### Static checks

Examples include totals, percentages, rates, metric identities, benchmark deltas, dataset splits, sensitivity-table arithmetic, confidence intervals, and reported p-values when inputs are available.

Never infer a missing denominator, exclusion, or hidden filter silently.

### Statistical checks

Record the statistic, assumptions, dependence structure, correction for repeated comparisons, loss definition, and whether the published inputs are sufficient. Distinguish arithmetic reproducibility from appropriateness of the statistical method.

### Public-data smoke checks

Before a large download:

- make a tiny request;
- record endpoint/version, parameters, date, and licence;
- verify historical retention and schema;
- report gaps, duplicates, missing entities, and failures;
- define the proxy boundary before using fallback data.

### Gate C — claims and metrics

Do not compare outcomes until denominators, filters, exclusions, missing-data policy, benchmark construction, timestamps, and extraction confidence are explicit.

## Phase 4 — replication design

Map paper components to repository components before coding.

| Paper component | Required decision |
| --- | --- |
| Inputs | Exact, inferred, proxy, synthetic, or unavailable? |
| Preprocessing | Are order, parameters, filtering, and missing-value behaviour known? |
| Model/agent | Are weights, prompts, provider, seeds, and version available? |
| Runtime pipeline | Are gates, retries, concurrency, intervention, and failure behaviour known? |
| Evaluation | Are metrics, denominators, benchmark, and post-processing equivalent? |

### Gate D — implementation value

Proceed only when the proposed code tests a material claim or narrows a meaningful uncertainty. Build the smallest auditable implementation that exercises that boundary.

Implementation principles:

- keep deterministic and stochastic paths separate;
- make assumptions and fallbacks explicit;
- preserve raw inputs and full outputs locally, committing only reviewed compact evidence;
- prefer stage boundaries and structured records over a monolithic notebook;
- test accounting, contracts, edge cases, and CLI smoke paths;
- label calibration as calibration;
- never tune solely to recover the headline number.

## Phase 5 — LLM and agentic systems

Request exact system/developer/tool prompts, model and provider versions, quantisation, sampling parameters, tool outputs, memory/retrieval context, safety outcomes, raw structured outputs, retry/repair/fallback logic, cost, latency, and errors.

Rules:

- a different model or provider is a behavioural comparison or proxy;
- validate outputs field by field;
- allow only bounded, audited repair;
- distinguish valid abstention, schema failure, provider failure, deterministic fallback, hard-gate rejection, and not-evaluated stages;
- report metrics and error histograms by provenance;
- do not label behaviour conservative, aggressive, safe, or biased until integration failures are separated from valid choices;
- record provider-side versioning limits and whether deterministic replay is actually possible.

## Phase 6 — environment, budget, and run readiness

Every promoted run should record:

- exact command, commit, start/end time, and timezone;
- OS and architecture;
- runtime version and dependency-lock digest;
- container image digest and relevant hardware;
- seeds and determinism limitations;
- external model/provider/API versions;
- input source, coverage, selected entities, size, and hashes;
- output summaries, report hashes, errors, and local-only artefacts.

Estimate runtime, storage/download volume, API/model calls, and monetary cost. Name the approval owner and threshold.

### Gate E — expensive run readiness

Do not start a credentialled or expensive run until:

- static, tiny-run, and contract tests pass;
- provenance and evidence capture are implemented;
- secrets are externalised;
- budget and stopping conditions are approved;
- failure modes leave an auditable result rather than an ambiguous partial run.

## Phase 7 — evidence and retention

The universal rule is policy-driven rather than repository-path-specific. Each project must generate its own retention policy.

Commit by default:

- source, tests, configuration, small fixtures, and prompts safe for release;
- claim ledgers, plans, decision logs, and reviewed reports;
- non-secret manifests and compact evidence bundles;
- coverage summaries and negative findings.

Keep local or external by default:

- full raw datasets and large generated outputs;
- databases, checkpoints, caches, and provider logs;
- raw prompts/completions when sensitive, secret-bearing, restricted, or high-volume;
- credentials, cookies, account identifiers, and private endpoints.

External evidence should record location, owner, checksum, and retention period.

## Phase 8 — testing

Tests should protect conclusions, not only code. Include as applicable:

- formula and denominator tests;
- parser and extraction fixtures;
- data coverage and duplicate checks;
- metric and stage-accounting tests;
- golden tiny runs;
- CLI smoke tests;
- LLM contract and bounded-repair tests using fake providers;
- evidence schema and drift tests;
- documentation-link validation.

Record exact commands and results in promoted reports.

## Phase 9 — reporting

Lead with what is supported, unsupported, contradicted, and unresolved.

Recommended structure:

1. executive conclusion;
2. frozen paper version and scope;
3. artefact/legal/environment summary;
4. prioritised claim-ledger summary;
5. static and statistical validation;
6. data reconstruction or proxy analysis;
7. functional/independent replication design and results;
8. comparison to paper;
9. negative findings and contradictions;
10. evidence, commands, and run provenance;
11. stopping decisions and required author artefacts;
12. independent review;
13. final assessment.

Avoid phrases such as `we reproduced the paper`, `same experiment`, or `confirmed the live system` unless the strict definition is satisfied.

## Phase 10 — independent conclusion review

A reviewer working from a clean context should verify:

- paper locations and extracted values;
- formulas, denominators, filters, and benchmark definitions;
- claim statuses and evidence references;
- environment and run provenance;
- consistency between machine-readable evidence and narrative reports;
- unsupported inferences and reproduction language.

Record the reviewed commit, discrepancies, corrections, and final decision.

### Gate F — publishable conclusion

Publish or merge the final assessment only when the clean-context review agrees that the evidence supports the language used.

## Stopping rules

Stop or downgrade a path when:

- an indispensable original artefact is unavailable;
- documented retention excludes the historical data;
- a material substitution breaks equivalence;
- repeated recovery attempts no longer add evidence;
- further tuning is aimed only at matching the paper;
- stochastic/LLM contracts or provenance are inadequate;
- the run exceeds approved cost or runtime;
- an author-dependent ambiguity reaches its recorded response deadline.

Preserve the reason, evidence, and consequence.

## Issue and PR workflow

Use claim-scoped issues rather than one broad `replicate paper` issue. Typical work items are intake, claim ledger, static validation, data/legal smoke, component diagnostic, minimal implementation, promoted run, evidence bundle, comparison report, negative finding, and independent final review.

Each PR should identify claim IDs, commands/tests, evidence outputs, limitations, stopping consequences, and whether it closes or merely informs the issue. Avoid mixing governance changes, broad documentation restructuring, implementation, and generated results without a clear necessity.

## Final conclusion pattern

```text
The available evidence supports <narrow conclusion>. The project classification is <direct reproduction / independent replication / proxy replication / functional replication / synthetic replication / diagnostic validation>. It does not support <broader conclusion> because <missing artefacts, material substitutions, contradiction, or review limitation>. The remaining uncertainty is <unresolved dependency>.
```
