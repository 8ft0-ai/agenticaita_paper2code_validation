# Paper Validation Guides — Start Here

Use this directory to start and govern a new paper-validation or replication project. The success criterion is not matching the paper's headline number. It is reaching the strongest conclusion justified by traceable evidence.

## Operational workflow

1. Freeze the paper version and record the access date.
2. Extract and prioritise headline claims before implementation.
3. Complete the artefact, legal, and retention inventory.
4. Decide the project classification and record Gate A.
5. Implement static checks for critical claims first.
6. Smoke-test public data and external services before bulk use.
7. Define denominators, exclusions, benchmark construction, and evidence outputs.
8. Build the smallest implementation that exercises the prioritised claim boundary.
9. Capture environment, provenance, fallbacks, decisions, outputs, and checksums.
10. Stop or downgrade scope when a gate fails; do not tune only to recover the reported number.
11. Run promoted experiments only after cost, credentials, contracts, and evidence capture are ready.
12. Complete an independent clean-context conclusion review before publishing.

## Decision gates

| Gate | Required decision |
| --- | --- |
| A — scope and artefacts | Is direct reproduction possible, and which claims justify further work? |
| B — data and legal adequacy | Can the required inputs be acquired, retained, and used lawfully at the required fidelity? |
| C — claims and metrics | Are extraction, denominators, exclusions, formulas, and benchmarks defined well enough to compare? |
| D — implementation value | Will the proposed code test a material claim rather than merely resemble the architecture? |
| E — expensive run readiness | Are tests, budgets, credentials, contracts, provenance, and evidence capture ready? |
| F — independent review | Does a clean-context reviewer agree that the evidence supports the final language? |

Record every gate in the generated `docs/decisions/gate_log.md`.

## Claim priority

Classify each claim by:

- `claim_importance`: `headline`, `supporting`, or `contextual`;
- `validation_priority`: `critical`, `useful`, or `optional`.

Validate critical headline claims first. A project need not exhaustively reproduce every descriptive statistic when the central conclusion is already bounded by unavailable artefacts or a material contradiction.

## Stopping rules

Stop or explicitly downgrade scope when:

- an indispensable original artefact is unavailable;
- documented retention proves the required historical data cannot be recovered;
- a substitute materially changes the data, model, provider, benchmark, or runtime;
- further calibration is aimed only at matching the paper's aggregate result;
- an LLM or stochastic path lacks tested contracts, provenance, or bounded failure handling;
- cost or runtime exceeds the approved budget;
- an author-dependent question remains unanswered after the project's defined contact period.

A documented negative finding is a successful output.

## Document map

| Document | Use |
| --- | --- |
| [Full playbook](arxiv_paper_validation_replication_playbook.md) | Methodological reference and reporting standard |
| [Bootstrap process](paper_project_bootstrap_process.md) | How to create and operate a new repository |
| [Fast checklists](paper_validation_checklists.md) | Day-to-day execution aid |
| [Review rubric](paper_project_review_rubric.md) | Milestone and final quality review |
| [Claim language](reproduction_claim_language.md) | Precise reproduction and replication terminology |
| [`bootstrap_paper_project.py`](bootstrap_paper_project.py) | Dependency-free scaffold generator |

Repository-specific commands, contribution rules, credentials, and exclusions belong in the generated `PROJECT_PROFILE.md`, not in the universal playbook.

## Quick start

```bash
python docs/guides/bootstrap_paper_project.py \
  --project-dir ../new_paper_validation \
  --title "Paper Title" \
  --arxiv-id "2501.01234" \
  --paper-version "v2" \
  --with-issue-specs \
  --with-ci
```

Review the dry-run plan first when integrating into an existing workspace:

```bash
python docs/guides/bootstrap_paper_project.py \
  --project-dir ../new_paper_validation \
  --title "Paper Title" \
  --arxiv-id "2501.01234" \
  --paper-version "v2" \
  --dry-run
```