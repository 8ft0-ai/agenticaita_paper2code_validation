# Paper Validation Project Bootstrap Process

Date: 2026-07-11

Start with [the operational guide](README.md). This document explains the generated scaffold and the decisions required before implementation expands.

## Create the scaffold

```bash
python docs/guides/bootstrap_paper_project.py \
  --project-dir ../new_paper_validation \
  --title "Paper Title" \
  --arxiv-id "2501.01234" \
  --paper-version "v2" \
  --authors "A. Author; B. Author" \
  --field "machine learning" \
  --task "benchmark replication" \
  --with-issue-specs \
  --with-ci
```

The paper version is required; the script will not silently assume `v1`. The arXiv URL is derived automatically unless supplied explicitly.

Use `--dry-run` to inspect the generated file plan. A non-empty target is refused by default. Use `--update-missing` to add only absent scaffold files. `--force` deliberately replaces generated paths and should be used only after reviewing the plan. `--update-missing` and `--force` are mutually exclusive.

The deprecated `--with-issues` alias remains accepted for compatibility, but the option creates issue specifications rather than remote GitHub issues. Prefer `--with-issue-specs`.

## Generated project controls

The scaffold creates:

```text
<project>/
  README.md
  PROJECT_PROFILE.md
  .paper-validation-scaffold.json
  docs/
    intake/paper_intake.md
    claims/claim_ledger.csv
    claims/claim_status_guide.md
    artifacts/artifact_inventory.md
    artifacts/artifact_request.md
    governance/data_and_licensing.md
    governance/retention_policy.md
    decisions/gate_log.md
    versions/paper_version_log.md
    validation/validation_plan.md
    replication/replication_plan.md
    review/final_independent_review.md
    reports/final_report_template.md
  validation/README.md
  replication/README.md
  scripts/README.md
  tests/README.md
```

`--with-issue-specs` adds claim-scoped work items under `docs/issues/`. `--with-ci` adds a minimal workflow that checks committed file size, runs Python tests only when test files exist, and validates relative Markdown links.

## First-day sequence

### 1. Freeze paper identity

Complete `docs/intake/paper_intake.md` and `docs/versions/paper_version_log.md`. A later arXiv revision must create a version-diff record; do not silently replace the claim ledger.

### 2. Prioritise claims

Populate the claim ledger with stable IDs. Record:

- paper version and location;
- claim type and importance;
- critical/useful/optional validation priority;
- extraction method, confidence, and manual verification;
- dependencies, validation method, evidence references, status, and rationale.

Critical headline claims should be validated before contextual or descriptive claims.

### 3. Complete artefact and legal inventory

Record released and missing artefacts, their claim dependencies, licence and retention constraints, and reproduction consequences. Complete `docs/governance/data_and_licensing.md` before bulk acquisition or redistribution.

### 4. Record Gate A

Choose the narrowest accurate project classification:

- direct reproduction;
- independent replication;
- proxy replication;
- functional replication;
- synthetic replication;
- diagnostic validation.

If required original artefacts are absent, direct reproduction stops. Continue only where the remaining validation or implementation tests a material claim.

## Before implementation

### Gate B — data and legal adequacy

Smoke-test sources before bulk download. Verify exact window, entities, granularity, schema, rate limits, licence, redistribution rights, and retention. A materially different source is a proxy, not the same experiment.

### Gate C — claims and metrics

Define denominators, exclusions, missing-data handling, benchmark construction, statistical assumptions, and extraction confidence. Do not compare figures until these are explicit.

### Gate D — implementation value

Map each paper component to a repository component and claim ID. Implement the smallest runnable path that can alter the conclusion. Do not build a broad architecture merely because the paper describes one.

## Before expensive runs

Complete Gate E:

- static and tiny-run tests pass;
- stochastic/LLM contracts and bounded repair/fallback paths are tested;
- environment and dependency capture is ready;
- cost, storage, runtime, and API budget are approved;
- credentials are supplied through secrets rather than committed files;
- manifests, provenance logs, summaries, and evidence bundles will be emitted;
- stopping criteria are written.

## Reporting and review

Every promoted run should record:

- commit, exact command, timestamps, OS/architecture, runtime and dependency digest;
- container and hardware details when relevant;
- timezone and random seeds or determinism limitations;
- data source, coverage, selected entities, and input hashes;
- provider/model/API versions for external services;
- decision provenance, repairs, fallbacks, and errors where applicable;
- output summaries, report hashes, and local-only artefacts.

Before the final report is published, Gate F requires a clean-context reviewer to compare paper locations, extracted values, calculations, denominators, statuses, evidence, and narrative language. The reviewer records the checked commit and any required corrections in `docs/review/final_independent_review.md`.

## Canonical templates

The files under `docs/guides/templates/` are the canonical sources for the claim ledger, artefact inventory, validation plan, replication plan, and final report. The script loads them by default. `--template-dir` may point to a complete replacement set with the same filenames.

Required template filenames:

- `claim_ledger.csv`
- `artifact_inventory.md`
- `validation_plan.md`
- `replication_plan.md`
- `final_report.md`

The generator fails clearly when a required template is missing.

## Recommended stopping decisions

- Preserve an unrecoverable data window as a negative finding rather than repeatedly retrying incompatible APIs.
- Do not run a different model/provider and call it reproduction of the original model path.
- Do not continue calibration solely to approach a reported metric.
- Close author-dependent questions as unresolved after the contact period recorded in the project plan.
- Stop expensive runs when the approved budget or evidence-quality threshold is breached.

The end state is successful when the project makes the evidence boundary clearer, even when the conclusion is that the original result is not independently reproducible.
