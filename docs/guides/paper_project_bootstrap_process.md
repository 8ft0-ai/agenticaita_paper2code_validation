# Paper Validation Project Bootstrap Process

Date: 2026-07-11

## Purpose

Use this process when starting a new arXiv paper validation or replication project. The goal is to create a clean workspace that separates intake, claim validation, artefact audit, data reconstruction, functional replication, evidence packaging, and final reporting from day one.

This guide pairs with [`bootstrap_paper_project.py`](bootstrap_paper_project.py), a small script that creates a starter project scaffold and Markdown/CSV templates.

## Bootstrap Principles

- Start with claims and artefacts, not code.
- Make the reproduction boundary explicit before implementation.
- Keep validation and replication separate.
- Preserve negative findings as project outputs.
- Commit small templates, reports, manifests, and evidence summaries.
- Keep raw data, large generated outputs, secrets, and provider logs outside git by default.
- Require every final claim to trace back to a paper location, artefact, command, or explicit limitation.

## Recommended Bootstrap Flow

### Step 1: Create the Project Scaffold

From this repository, run:

```bash
python docs/guides/bootstrap_paper_project.py \
  --project-dir ../new_paper_validation \
  --title "Paper Title" \
  --arxiv-id "2501.01234" \
  --paper-version "v1"
```

Add optional metadata when known:

```bash
python docs/guides/bootstrap_paper_project.py \
  --project-dir ../new_paper_validation \
  --title "Paper Title" \
  --arxiv-id "2501.01234" \
  --paper-version "v1" \
  --paper-url "https://arxiv.org/abs/2501.01234" \
  --authors "A. Author; B. Author" \
  --field "machine learning" \
  --task "benchmark replication"
```

Generate starter issue specs and a minimal CI workflow when useful:

```bash
python docs/guides/bootstrap_paper_project.py \
  --project-dir ../new_paper_validation \
  --title "Paper Title" \
  --arxiv-id "2501.01234" \
  --with-issues \
  --with-ci
```

Use standalone template overrides from a directory when the default templates need local customization:

```bash
python docs/guides/bootstrap_paper_project.py \
  --project-dir ../new_paper_validation \
  --title "Paper Title" \
  --arxiv-id "2501.01234" \
  --template-dir docs/guides/templates
```

Recognized template override filenames are:

- `claim_ledger.csv`;
- `artifact_inventory.md`;
- `validation_plan.md`;
- `replication_plan.md`;
- `final_report.md`.

The script refuses to overwrite an existing non-empty directory unless `--force` is used. Prefer creating a fresh directory instead of forcing over previous work.

### Step 2: Fill the Intake Brief

Edit `docs/intake/paper_intake.md` before writing implementation code.

Minimum information:

- exact paper version;
- date accessed;
- headline claims;
- claimed datasets and benchmarks;
- released artefacts;
- missing artefacts;
- initial reproduction scope.

The intake brief should end with a precise scope statement such as:

```text
This project will validate paper-level arithmetic and implement a functional replication on public data. It will not claim empirical reproduction unless the original dataset, runtime logs, configuration, and evaluation artefacts are provided.
```

### Step 3: Build the Claim Ledger

Populate `docs/claims/claim_ledger.csv` with every material claim before implementation expands.

Start with:

- abstract headline result;
- main table metrics;
- benchmark comparisons;
- dataset sizes and filters;
- training or runtime settings;
- autonomy, live-system, or zero-intervention claims;
- cost, latency, robustness, and generalization claims.

Use stable claim IDs such as `C001`, `C002`, and so on. Every final report section should cite these IDs.

### Step 4: Complete the Artefact Audit

Edit `docs/artifacts/artifact_inventory.md` and `docs/artifacts/artifact_request.md`.

Classify each required artefact as:

- available and committed;
- available externally;
- reconstructable from public sources;
- unavailable;
- ambiguous;
- not applicable.

If an artefact is unavailable, write the consequence. For example:

```text
Original prompt/completion logs are unavailable. Therefore LLM behavioural claims can be compared against a new model run, but the original decision path cannot be independently reproduced.
```

### Step 5: Write the Validation Plan

Edit `docs/validation/validation_plan.md`.

Define:

- static arithmetic checks;
- statistical recomputations;
- parser requirements;
- public-data availability checks;
- unsupported claims and why;
- expected outputs.

Do not wait for implementation to decide what `supported`, `partially supported`, `unsupported`, and `contradicted` mean.

### Step 6: Write the Replication Plan

Edit `docs/replication/replication_plan.md`.

Decide whether the project is attempting:

- direct rerun;
- clean-room functional replication;
- public-data proxy replication;
- synthetic replication;
- component diagnostic.

Map paper components to repository components before coding. If a paper component is underspecified, record the assumption in the plan.

### Step 7: Establish Data and Evidence Policy

Review `docs/evidence/evidence_plan.md` and `.gitignore`.

Default policy:

- `data/` is local and gitignored;
- `results/` is local and gitignored;
- `docs/evidence/` is for compact, non-secret evidence bundles;
- raw provider logs, API responses, model completions, and large generated outputs are not committed by default.

### Step 8: Add Minimal Code Only After Plans Exist

Use these starter directories:

- `validation/` for claim checks and static validation;
- `replication/` for functional implementation;
- `scripts/` for standalone tooling;
- `tests/` for root-level tests.

Recommended first code tasks:

1. Implement claim-ledger loading and status summaries.
2. Implement one or two static validation checks.
3. Add tests for those checks.
4. Add a tiny CLI smoke path.
5. Only then start public-data fetching or model replication.

### Step 9: Create Issues or Work Items

If using GitHub Issues, open scoped issues in this order:

1. Paper intake and artefact inventory.
2. Claim ledger extraction.
3. Static validation checks.
4. Data availability smoke test.
5. Public-data reconstruction, if applicable.
6. Functional architecture skeleton.
7. End-to-end tiny run.
8. Full run and evidence bundle.
9. Comparison report.
10. Final assessment.

Avoid a single broad issue named `replicate paper`. It causes scope drift and encourages overclaiming.

### Step 10: First Milestone Review

Before large implementation work, perform a milestone review using `docs/reports/milestone_review.md`.

The review should answer:

- Which claims are already checkable?
- Which claims require missing artefacts?
- Which data sources are available?
- What is the exact replication type?
- What would change the final conclusion?

If the answer is already `not reproducible from available artefacts`, keep going only if functional replication or diagnostic validation is still valuable.

## Scaffold Layout

The bootstrap script creates this structure:

```text
<project>/
  README.md
  .gitignore
  docs/
    intake/
      paper_intake.md
    claims/
      claim_ledger.csv
      claim_status_guide.md
    artifacts/
      artifact_inventory.md
      artifact_request.md
    validation/
      validation_plan.md
    replication/
      replication_plan.md
    evidence/
      evidence_plan.md
      evidence_bundle_template.json
    reports/
      milestone_review.md
      final_report_template.md
  validation/
    README.md
  replication/
    README.md
  scripts/
    README.md
  tests/
    README.md
```

With `--with-issues`, the scaffold also includes:

```text
docs/issues/
  01-paper-intake.md
  02-claim-ledger.md
  03-static-validation.md
  04-data-smoke.md
  05-replication-skeleton.md
  06-evidence-bundle.md
  07-final-assessment.md
```

With `--with-ci`, the scaffold also includes:

```text
.github/workflows/validation-smoke.yml
```

## First-Day Checklist

- Run the bootstrap script.
- Commit the empty scaffold or open an initial PR.
- Fill `paper_intake.md`.
- Add at least 10 high-value claims to `claim_ledger.csv`.
- Fill the artefact inventory enough to identify reproduction blockers.
- Write a one-paragraph scope statement in `README.md`.
- Decide whether direct empirical reproduction is possible.
- Open scoped issues or create a local task list.

## First-Week Checklist

- Finish the claim ledger for all headline claims.
- Implement static validation for all recomputable arithmetic claims.
- Add tests for every validation formula.
- Smoke-test any public data source before bulk download.
- Write a data coverage report template before fetching large data.
- Draft the replication component mapping.
- Create compact evidence format before running expensive jobs.
- Preserve all negative findings in docs.

## Decision Gates

### Gate A: Is Empirical Reproduction Possible?

Empirical reproduction is possible only if the original or equivalent artefacts exist:

- raw input data;
- preprocessing code or exact transformations;
- model/configuration details;
- runtime seeds or stochastic controls;
- evaluation scripts;
- original logs or checkpoints for live/agentic systems.

If not, downgrade scope to validation, functional replication, public-data proxy, or diagnostic reproduction.

### Gate B: Is Public Data Adequate?

Public data is adequate only if it covers the relevant time window, entities, schema, and granularity. If it differs materially, label it as fallback or proxy data.

### Gate C: Are Metrics Well-Defined?

Do not compare metrics until denominators, filters, exclusions, benchmark construction, and missing-data handling are clear.

### Gate D: Are Outputs Auditable?

Every run should produce enough logs, summaries, manifests, and compact evidence for another reviewer to understand what happened without full local artefacts.

## Recommended Naming Conventions

Use names that preserve the project boundary:

- `validation_report.md` for paper-claim checks.
- `artifact_inventory.md` for available/missing evidence.
- `public_data_reconstruction_report.md` for public API or dataset recovery.
- `functional_replication_report.md` for executable architecture results.
- `comparison_to_paper.md` for paper-vs-run comparisons.
- `final_assessment.md` for the concluding interpretation.

Avoid names like `reproduction_report.md` unless the original empirical artefacts are actually available.

## Bootstrap Script Maintenance

The script is intentionally dependency-free and uses only the Python standard library. Update it when the playbook changes materially.

Good future additions:

- optional Git initialization;
- optional Python package or no-package layout choice;
- optional claim-ledger JSON schema;
- optional evidence-bundle validator.

Keep the default scaffold small. The purpose is to force good project framing, not to generate a large framework.
