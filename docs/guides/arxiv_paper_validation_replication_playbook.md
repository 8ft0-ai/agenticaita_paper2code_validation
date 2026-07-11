# arXiv Paper Validation and Replication Playbook

Date: 2026-07-11

## Purpose

Use this guide the next time we want to validate or replicate an arXiv paper. It is designed for papers where the goal is not just to produce code that resembles the method, but to make a defensible statement about what can and cannot be independently verified.

The central rule is simple:

> Separate paper-claim validation, public-data reconstruction, and functional architecture replication. Do not call a result an empirical reproduction unless the original data, decisions, runtime context, and evaluation artefacts are available.

This playbook is intentionally conservative. It treats missing artefacts, failed data recovery, incompatible public APIs, malformed model outputs, and contradictory benchmark definitions as first-class findings rather than inconveniences to hide.

## Definitions

| Term | Meaning |
| --- | --- |
| Static validation | Checking claims that can be recomputed from the paper text, tables, equations, appendices, and released files. |
| Artefact audit | Inventorying what the paper releases and what it would need for full reproduction. |
| Public-data reconstruction | Rebuilding inputs from public APIs or datasets when the original inputs are not released. |
| Functional replication | Implementing the described architecture so it can run and produce comparable outputs. |
| Empirical reproduction | Re-running the original experiment against the original or equivalent artefacts and recovering the reported result. |
| Negative finding | Evidence that a requested reproduction path is impossible, unsupported, stale, unavailable, or materially under-documented. |

## Phase 0: Intake and Scope Decision

Start by deciding what kind of project this is. Most papers will not support full empirical reproduction from the PDF alone.

### Intake Checklist

- Record paper title, arXiv ID, version, date accessed, authors, and claimed task.
- Save or reference the exact PDF/source version used for the audit.
- Identify the headline claims before reading implementation details.
- Identify whether the paper is empirical, theoretical, benchmark-driven, simulation-driven, or system/demo-driven.
- Note whether the paper claims live operation, autonomous operation, proprietary data, private logs, closed-source models, or unreleased prompts.
- Decide whether the expected output is validation, replication, reproduction, or a narrower diagnostic.

### Initial Scope Statement Template

```text
This project validates and/or replicates <paper title> (<arXiv ID>, version <version>).

Supported goals:
- Check arithmetic/statistical consistency of reported claims.
- Build an executable approximation of the described method.
- Reconstruct public-data-dependent inputs where possible.
- Produce auditable outputs and identify missing artefacts.

Unsupported unless authors provide artefacts:
- Exact reproduction of private datasets, runtime logs, prompts, model outputs, human interventions, or execution-time state.
```

## Phase 1: Artefact Inventory

Before writing code, inventory what exists. This prevents the project from drifting into an overclaim.

### Artefact Categories

| Category | Examples | Reproduction Impact |
| --- | --- | --- |
| Paper text | PDF, LaTeX source, appendix, tables, equations | Enables static validation. |
| Code | Repository, scripts, notebooks, Dockerfiles | Enables direct or partial rerun. |
| Raw data | Training data, market data, sensor logs, benchmark inputs | Required for empirical reproduction. |
| Processed data | Feature matrices, splits, embeddings, labels | May support reproduction if provenance is clear. |
| Runtime logs | Audit logs, run manifests, seeds, traces, checkpoints | Required to validate execution path. |
| Model artefacts | Weights, prompts, completions, hyperparameters | Required for ML/LLM behavioural reproduction. |
| Environment | Dependency lockfiles, hardware, API versions, exchange endpoints | Required to distinguish method differences from environment drift. |
| Evaluation artefacts | Metrics scripts, benchmark definitions, scoring code | Required to validate headline outcomes. |

### Artefact Request Template

Create an artefact request early if anything material is missing:

```text
To independently reproduce the reported experiment, we need:

1. Exact raw input dataset(s), including timestamps, symbols/entities, filters, and exclusions.
2. Processed datasets or scripts that generate them from raw inputs.
3. Original train/validation/test splits or sampling seeds.
4. Full configuration used for each reported run.
5. Runtime logs, audit traces, decisions, and failure/retry records.
6. Model identifiers, weights, prompts, sampling parameters, and provider/server details.
7. Evaluation scripts and benchmark construction logic.
8. Dependency versions, hardware assumptions, and external API versions.
9. Any manual intervention, filtering, tuning, or post-processing records.
```

### Artefact Classification

Every important claim should be classified as one of:

- `recomputable_from_paper`
- `recomputable_from_released_artefacts`
- `reconstructable_from_public_data`
- `functionally_replicable_only`
- `unsupported_without_author_artefacts`
- `contradictory_or_ambiguous`

This classification should appear in the final report.

## Phase 2: Claim Ledger

Build a claim ledger before implementation. This is the backbone of the validation.

### What to Extract

- Headline results from abstract, introduction, conclusion, and tables.
- Counts, rates, percentages, confidence intervals, p-values, effect sizes, and benchmarks.
- Dataset sizes, time windows, assets/classes/entities, filters, and exclusions.
- Model names, prompts, hyperparameters, seeds, hardware, and runtime settings.
- Claims about autonomy, zero intervention, live execution, robustness, cost, latency, or generality.
- Any implied arithmetic relationships, such as `wins + losses = trades` or `precision = TP / (TP + FP)`.

### Claim Ledger Schema

Use a CSV, JSON, or Markdown table with at least these fields:

| Field | Purpose |
| --- | --- |
| `claim_id` | Stable identifier such as `C001`. |
| `location` | Paper section, page, table, figure, equation, or appendix. |
| `claim_text` | Exact or near-exact claim. |
| `reported_value` | Number or qualitative assertion. |
| `dependencies` | Data, code, logs, model, benchmark, or assumptions needed. |
| `validation_method` | Arithmetic check, statistical recomputation, code rerun, public-data reconstruction, or manual review. |
| `status` | Supported, partially supported, unsupported, contradicted, not testable. |
| `notes` | Caveats, missing artefacts, formula used, or reproduction boundary. |

### Status Rules

- Use `supported` only when the claim can be independently recomputed or observed from available artefacts.
- Use `partially_supported` when a narrower version is supported but the full claim needs missing context.
- Use `unsupported` when required artefacts are absent.
- Use `contradicted` when available evidence conflicts with the claim or with another paper statement.
- Use `not_testable` when the claim is too vague to operationalize.

## Phase 3: Validation Plan

Validation answers: are the paper's reported claims internally consistent and externally checkable?

### Static Validation

Implement static checks first. They are cheap, deterministic, and often reveal whether the paper's own numbers cohere.

Good static checks include:

- Sums and count reconciliation.
- Percentages and rates.
- Profit/loss or score relationships.
- Confusion-matrix-derived metrics.
- Benchmark deltas and alpha calculations.
- Confidence intervals and p-values when enough inputs are reported.
- Sensitivity-table arithmetic.
- Dataset split totals.

Static validation should not silently infer missing denominators or hidden filters. If a formula requires an unreported value, mark the claim as unsupported or partially supported.

### Statistical Validation

If the paper reports significance, confidence, or distributional claims:

- Recompute the reported statistic from published counts if possible.
- Check whether the test is appropriate for the stated data generating process.
- Check whether repeated comparisons require correction.
- Distinguish arithmetic reproducibility from statistical validity.
- Report exact assumptions used for any recomputation.

### Public-Data Validation

If the paper used public data, validate availability before building the model:

- Confirm the endpoint, dataset, license, retention window, schema, and rate limits.
- Run a tiny smoke fetch before a full download.
- Record request parameters and timestamps.
- Store coverage metadata, missing intervals, duplicate keys, and per-entity failures.
- Check whether current public data can actually recover the paper's historical window.
- Treat fallback data sources as comparators, not replacements for the original dataset.

### Validation Report Minimum Contents

- Paper identity and version.
- Summary of supported, partially supported, unsupported, and contradicted claims.
- Claim ledger or pointer to it.
- Exact formulas used.
- Commands run.
- Artefacts required but missing.
- Clear distinction between internal consistency and empirical reproduction.

## Phase 4: Replication Design

Replication answers: can we build an executable system that approximates the described method closely enough to produce auditable comparable artefacts?

### Decide the Replication Type

| Type | Use When | Claim You May Make |
| --- | --- | --- |
| Direct rerun | Original code and data are available. | The released artefacts reproduce or fail to reproduce the reported result. |
| Clean-room functional replication | Method is described but code/data are missing. | The described architecture can be implemented and exercised. |
| Public-data proxy replication | Original data are missing but public proxies exist. | The method behaves this way on comparable public data. |
| Synthetic replication | No adequate real data are available. | The implementation mechanics work under controlled inputs. |
| Diagnostic reproduction | Only a specific component is testable. | This component is or is not consistent with the paper. |

### Architecture Mapping

Create a mapping table before coding:

| Paper Component | Repository Component | Fidelity | Missing Details |
| --- | --- | --- | --- |
| Input data | Loader/exporter | Exact, proxy, synthetic, or unavailable | Source, filters, sampling, schema. |
| Preprocessing | Transform function/script | Exact or inferred | Parameters, order, missing value policy. |
| Model/agent | Implementation module | Exact, compatible, or proxy | Weights, prompts, seeds, provider. |
| Decision logic | Pipeline/stage code | Exact or approximated | Hidden gates, manual overrides. |
| Evaluation | Metric script | Exact or comparable | Benchmark construction, denominators. |

### Minimal Implementation Principles

- Implement the smallest runnable version that tests the claim boundary.
- Keep deterministic and stochastic paths separate.
- Preserve raw inputs and generated outputs locally, but commit only small curated evidence.
- Make every fallback explicit in logs and summaries.
- Prefer clear stage boundaries over a monolithic notebook.
- Add tests for accounting, schema contracts, edge cases, and CLI smoke paths.
- Do not tune toward the paper's headline result without documenting calibration as calibration.

### Output Artefacts

A useful replication run should produce:

- Run manifest with command, git commit, config, input paths, and timestamps.
- Input coverage report.
- Pipeline log or per-record decision trace.
- Summary metrics JSON.
- Main result table in CSV or JSON.
- Error/fallback/provenance log.
- Human-readable report.
- Compact evidence bundle with checksums and selected extracts.

## Phase 5: LLM and Agentic Systems

LLM papers need extra discipline because behaviour depends on unavailable prompts, provider state, sampling, safety filters, tool traces, and hidden retry logic.

### LLM Artefacts to Request

- Exact prompts, including system/developer/tool messages.
- Model identifier, version, quantisation, provider, and endpoint.
- Temperature, top-p, top-k, seed, max tokens, stop sequences, and tool settings.
- Raw completions and structured parsed outputs.
- Retry, repair, fallback, and validation rules.
- Conversation state, memory, retrieval context, and tool outputs.
- Safety filter or moderation outcomes.
- Cost, token usage, latency, and provider error logs.

### LLM Replication Rules

- Treat a different model/provider as a behavioural comparison, not exact reproduction.
- Validate structured outputs at field level.
- Allow bounded repair only if logged separately from first-pass validity.
- Distinguish valid model abstention from schema failure and deterministic fallback.
- Log decision provenance for every stage.
- Report contract-error histograms and fallback counts.
- Do not describe a model as conservative, aggressive, safe, or biased until integration failures are separated from valid model choices.

### LLM Provenance Categories

Use categories like:

- `llm_valid`
- `llm_repaired`
- `deterministic_fallback`
- `provider_error_fallback`
- `deterministic_hard_gate`
- `not_evaluated`

Summaries should show metrics by provenance, not just aggregate outcomes.

## Phase 6: Evidence and Retention

Large raw artefacts should usually stay local or in external storage. The repository should still contain enough compact evidence to make reports auditable.

Follow the repository retention policy in [../artifact_retention_policy.md](../artifact_retention_policy.md).

### Commit These

- Source code, tests, configs, and small prompts/templates.
- Claim ledgers and human-readable reports.
- Run manifests without secrets.
- Compact evidence bundles with checksums and selected summaries.
- Coverage summaries and small sample extracts.
- Documentation of failed attempts and negative findings.

### Do Not Commit By Default

- Full raw datasets.
- Large generated CSVs or SQLite databases.
- Full model audit logs if they include prompts, completions, secrets, or large volumes.
- API credentials, private endpoints, tokens, cookies, or account identifiers.
- Cache directories and temporary run outputs.

### Compact Evidence Bundle Template

```json
{
  "paper": {
    "title": "...",
    "arxiv_id": "...",
    "version": "..."
  },
  "run": {
    "command": "...",
    "git_commit": "...",
    "started_at": "...",
    "finished_at": "..."
  },
  "inputs": {
    "source": "...",
    "rows": 0,
    "entities": 0,
    "coverage_summary": "...",
    "checksums": {}
  },
  "outputs": {
    "summary_metrics": {},
    "result_counts": {},
    "checksums": {}
  },
  "limitations": []
}
```

## Phase 7: Testing and Verification

Tests should protect the conclusions, not just the code.

### Test Categories

- Formula tests for every static claim calculation.
- Parser tests for paper tables or released data files.
- Data coverage tests for missing, duplicate, or malformed inputs.
- Metric tests for denominators and edge cases.
- Pipeline-stage accounting tests.
- CLI smoke tests.
- Golden tiny-run tests using synthetic fixtures.
- LLM contract tests using fake providers.
- Link validation for documentation.
- Evidence-bundle schema tests.

### Verification Before Reporting

Run the relevant tests and smoke commands before writing final conclusions. Record exact commands and results in the report.

If tests are split across modules, document that explicitly. A fragmented test structure is acceptable if the required commands are clear.

## Phase 8: Reporting

The final report should lead with what is supported, what is not supported, and why. Do not bury missing artefacts after the result tables.

### Recommended Report Structure

1. Executive conclusion.
2. Scope and paper version.
3. Artefact availability summary.
4. Claim ledger summary.
5. Static validation results.
6. Public-data reconstruction results, if applicable.
7. Functional replication design.
8. Replication results and comparison to paper.
9. Negative findings and contradictions.
10. Reproducibility evidence and commands.
11. Limitations and required author artefacts.
12. Final assessment.

### Language to Use

Use precise phrases:

- `internally consistent`
- `supported by published arithmetic`
- `supported by released artefacts`
- `functionally replicated`
- `public-data proxy`
- `behavioural comparison`
- `unsupported without original artefacts`
- `not independently reproducible from available materials`

Avoid overclaiming phrases unless strictly true:

- `reproduced the paper`
- `validated the live experiment`
- `confirmed the authors' result`
- `proved the system works`
- `same data`
- `same model behaviour`

### Final Conclusion Template

```text
This repository supports a narrow conclusion: <paper title> is <internally consistent / partially consistent / contradicted> for claims that can be checked from available materials. The implemented system <does / does not> functionally approximate the described architecture on <released/public/synthetic> data. It does not independently reproduce the original empirical run because <missing artefacts> are unavailable.
```

## Phase 9: Issue Workflow

Break work into small, claim-scoped issues. Avoid giant issues like `replicate paper` without sub-issues.

### Useful Issue Types

- `paper-intake`: identify version, scope, artefacts, and headline claims.
- `claim-ledger`: extract and classify paper claims.
- `static-validation`: implement arithmetic/statistical checks.
- `data-reconstruction`: fetch or reconstruct public data and coverage reports.
- `method-implementation`: implement one architecture component.
- `pipeline-run`: execute an end-to-end run and preserve outputs.
- `comparison-report`: compare implementation outputs with paper claims.
- `negative-finding`: document unavailable data, API limits, or contradictions.
- `evidence-bundle`: create compact committed evidence.
- `final-assessment`: write the concluding report.

### Pull Request Rules

- Keep each PR scoped to one issue or one closely related claim group.
- Include commands run and test results.
- Include explicit limitations when touching empirical claims.
- Do not mix source changes, generated large data, and broad documentation rewrites unless necessary.
- If a PR discovers a new limitation, open or update an issue rather than hiding it in prose.

## Common Failure Modes

### Treating Functional Replication as Reproduction

If original artefacts are missing, the implementation can show that a method is plausible or executable. It cannot prove that the original run happened as reported.

### Silent Venue or Dataset Substitution

Fallback data can be useful, but it must be labelled as fallback. Differences in venue, benchmark, schema, liquidity, retention, filtering, and timestamps can change the conclusion.

### Matching Aggregate Metrics by Tuning

Calibration is acceptable when labelled. It is not evidence of reproduction unless the calibrated parameters are paper-grounded or independently justified.

### Ignoring Runtime Provenance

For live systems, model agents, trading systems, robotics, distributed systems, or human-in-the-loop systems, aggregate outputs are not enough. The decision path matters.

### Overlooking Denominators

Many paper contradictions come from denominator drift: total events, eligible events, approved events, executed events, completed events, and evaluated events may all differ.

### Losing Negative Findings

Failed API calls, retention limits, missing archives, unsupported claims, and ambiguous benchmarks are results. Preserve them.

## Quick Start Checklist

Use this checklist for a new paper:

1. Record paper identity and version.
2. Extract headline claims into a claim ledger.
3. Inventory released artefacts and missing artefacts.
4. Classify every major claim by reproducibility status.
5. Implement static validation before any full replication.
6. Smoke-test data availability before large downloads.
7. Decide direct, functional, public-data proxy, synthetic, or diagnostic replication.
8. Build the smallest auditable implementation that exercises the claim.
9. Log inputs, decisions, fallbacks, outputs, and metrics.
10. Add tests for claim formulas and pipeline accounting.
11. Generate compact evidence bundles instead of committing large outputs.
12. Write reports that distinguish validation, replication, and reproduction.
13. Preserve negative findings and missing artefact requirements.
14. Run tests and documentation link validation before finalizing.
15. End with a precise conclusion about what is supported and what remains unsupported.

## Final Standard

A good paper validation project should make the boundary clearer than the paper did. If the result is `not reproducible from available artefacts`, that is still a successful outcome when it is demonstrated with careful claim accounting, executable checks, preserved evidence, and honest reporting.
