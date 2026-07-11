# Paper Validation Checklists

Date: 2026-07-11

Use these checklists as the fast operational companion to the full arXiv paper validation playbook.

## Intake Checklist

- Record paper title, arXiv ID, version, URL, authors, and date accessed.
- Save or reference the exact PDF/source version reviewed.
- Identify headline claims from abstract, introduction, main tables, and conclusion.
- Identify whether the paper is empirical, theoretical, benchmark-driven, simulation-driven, or system/demo-driven.
- Note claims about live operation, autonomy, private data, unreleased prompts, closed models, manual intervention, or proprietary infrastructure.
- Write a one-paragraph scope statement before implementation begins.
- Decide whether the project target is validation, direct rerun, public-data proxy replication, functional replication, synthetic replication, or component diagnostic.

## Artefact Checklist

- Paper PDF/source available.
- Code repository available or explicitly absent.
- Raw data available, externally accessible, reconstructable, or unavailable.
- Processed data and split definitions available or unavailable.
- Model weights, prompts, completions, checkpoints, seeds, and configuration available or unavailable.
- Runtime logs, audit trails, tool traces, retry records, and failure records available or unavailable.
- Evaluation scripts and benchmark construction available or unavailable.
- Dependency versions, hardware, API versions, and external services documented or unavailable.
- Missing artefacts have explicit reproduction consequences.

## Claim-Ledger Checklist

- Every headline result has a claim ID.
- Every table metric needed for the conclusion has a claim ID.
- Dataset sizes, filters, exclusions, and time windows have claim IDs.
- Benchmark and baseline definitions have claim IDs.
- Autonomy, live-operation, cost, latency, robustness, and generalization claims have claim IDs.
- Each claim has a paper location.
- Each claim has dependencies and a validation method.
- Each claim status is one of `unreviewed`, `supported`, `partially_supported`, `unsupported`, `contradicted`, or `not_testable`.
- Unsupported claims state exactly which artefact is missing.

## Static Validation Checklist

- Recompute all reported percentages and rates.
- Reconcile totals, subtotals, and denominators.
- Recompute benchmark deltas and alpha claims.
- Recompute confusion-matrix-derived metrics where possible.
- Recompute statistical tests only when required inputs are reported.
- Mark claims unsupported when denominators or filters are missing.
- Add tests for every implemented formula.
- Record exact formulas in the validation report.

## Data Reconstruction Checklist

- Smoke-test the public data source before bulk download.
- Record endpoint, dataset version, license, schema, request parameters, and date accessed.
- Check coverage for the exact paper time window or split.
- Check entity/symbol/class coverage.
- Check duplicates, gaps, missing intervals, and schema drift.
- Preserve per-entity failures.
- Label fallback datasets as fallback or proxy data.
- Do not treat public-data proxy results as original empirical reproduction.

## Functional Replication Checklist

- Map every paper component to an implementation component.
- Record fidelity for each component: exact, inferred, proxy, synthetic, or unavailable.
- Keep deterministic and stochastic paths separate.
- Log fallbacks and assumptions.
- Produce run manifests, summaries, decision logs, and comparison reports.
- Add tests for pipeline-stage accounting and metric denominators.
- Avoid calibration unless it is labelled and justified.

## LLM and Agentic-System Checklist

- Request exact prompts, completions, model identifiers, provider details, and sampling parameters.
- Request tool traces, memory/retrieval context, retry rules, repair logic, and fallback policy.
- Treat different providers or models as behavioural comparisons, not exact reproduction.
- Validate structured model outputs field by field.
- Distinguish valid model abstention from schema failure and deterministic fallback.
- Log provenance categories for every decision.
- Report contract-error histograms, repair counts, fallback counts, and provider failures.
- Do not infer behavioural traits until integration failures are separated from valid model choices.

## Evidence Checklist

- Raw data and large generated outputs remain local by default.
- Secrets, credentials, private provider logs, and raw completions are not committed by default.
- Compact evidence bundles include paper identity, command, git commit, input summaries, output summaries, checksums, and limitations.
- Reports include commands and test results.
- Negative findings are documented as first-class outputs.

## Final Report Checklist

- Lead with supported and unsupported conclusions.
- State the paper version and access date.
- Include artefact availability summary.
- Include claim-ledger status summary.
- Separate static validation, data reconstruction, and functional replication.
- Label proxy data and synthetic data clearly.
- State all missing artefacts required for empirical reproduction.
- Avoid saying `reproduced` unless original artefacts and equivalent runtime context are available.
- Include exact commands and evidence locations.
- End with a precise conclusion about what is independently verified.
