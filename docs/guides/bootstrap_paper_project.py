#!/usr/bin/env python3
"""Bootstrap a new arXiv paper validation/replication workspace.

The generated scaffold is intentionally lightweight. It creates documentation
and directory boundaries that force claim-ledger, artefact, validation, and
replication decisions before substantial implementation begins.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path


def slugify(value: str) -> str:
    chars = []
    previous_dash = False
    for char in value.lower():
        if char.isalnum():
            chars.append(char)
            previous_dash = False
        elif not previous_dash:
            chars.append("-")
            previous_dash = True
    return "".join(chars).strip("-") or "paper-validation"


def write_file(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        raise SystemExit(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def metadata(args: argparse.Namespace) -> dict[str, str]:
    return {
        "title": args.title,
        "slug": slugify(args.title),
        "arxiv_id": args.arxiv_id,
        "paper_version": args.paper_version,
        "paper_url": args.paper_url or "TBD",
        "authors": args.authors or "TBD",
        "field": args.field or "TBD",
        "task": args.task or "TBD",
        "created": date.today().isoformat(),
    }


def readme(meta: dict[str, str]) -> str:
    return f"""# {meta['title']} Validation and Replication

Created: {meta['created']}

| Field | Value |
| --- | --- |
| Paper | {meta['title']} |
| arXiv ID | {meta['arxiv_id']} |
| Version | {meta['paper_version']} |
| URL | {meta['paper_url']} |
| Authors | {meta['authors']} |
| Field | {meta['field']} |
| Task | {meta['task']} |

## Scope

This project validates and/or replicates the paper above. The initial scope must be filled before implementation work expands.

Supported by default:

- paper-level arithmetic and statistical validation;
- artefact inventory and missing-evidence documentation;
- public-data reconstruction where sources are available;
- functional replication of described methods where implementation details are sufficient.

Not supported by default:

- exact empirical reproduction without original data, logs, configurations, model artefacts, prompts, and evaluation scripts;
- claims about live/autonomous execution without runtime provenance;
- claims that require private or unreleased artefacts.

## Starter Documents

- `docs/intake/paper_intake.md`
- `docs/claims/claim_ledger.csv`
- `docs/artifacts/artifact_inventory.md`
- `docs/artifacts/artifact_request.md`
- `docs/validation/validation_plan.md`
- `docs/replication/replication_plan.md`
- `docs/evidence/evidence_plan.md`
- `docs/reports/final_report_template.md`

## Local Artefact Policy

Raw data, generated results, caches, credentials, provider logs, and large outputs should remain local by default. Commit compact evidence bundles and human-readable reports only when they contain no secrets and are small enough for review.
"""


def gitignore() -> str:
    return """# Local data and generated outputs
data/
results/
outputs/
artifacts/local/
*.sqlite
*.db
*.parquet
*.feather
*.pkl
*.pickle

# Secrets and local environment
.env
.env.*
*.key
*.pem
*.token

# Python caches
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.mypy_cache/

# Notebooks and local scratch by default
.ipynb_checkpoints/
scratch/
tmp/
"""


def intake(meta: dict[str, str]) -> str:
    return f"""# Paper Intake

Date created: {meta['created']}

## Paper Identity

| Field | Value |
| --- | --- |
| Title | {meta['title']} |
| arXiv ID | {meta['arxiv_id']} |
| Version | {meta['paper_version']} |
| URL | {meta['paper_url']} |
| Authors | {meta['authors']} |
| Field | {meta['field']} |
| Task | {meta['task']} |

## Headline Claims

- TBD

## Claimed Data Sources

- TBD

## Claimed Method Components

- TBD

## Claimed Evaluation Setup

- TBD

## Released Artefacts

- TBD

## Missing Artefacts

- TBD

## Initial Reproduction Boundary

TBD. State whether this project targets static validation, direct rerun, public-data proxy replication, clean-room functional replication, synthetic replication, or a component diagnostic.

## Initial Scope Statement

TBD. Use precise language about what can and cannot be independently reproduced from available materials.
"""


def claim_ledger() -> str:
    return """claim_id,location,claim_text,reported_value,dependencies,validation_method,status,notes
C001,TBD,TBD,TBD,TBD,TBD,unreviewed,TBD
"""


def claim_status_guide() -> str:
    return """# Claim Status Guide

Use these statuses in `claim_ledger.csv`.

| Status | Meaning |
| --- | --- |
| `unreviewed` | Extracted but not evaluated yet. |
| `supported` | Independently recomputed or observed from available artefacts. |
| `partially_supported` | A narrower version is supported, but the full claim requires missing context. |
| `unsupported` | Required artefacts or details are unavailable. |
| `contradicted` | Available evidence conflicts with the claim or another paper statement. |
| `not_testable` | The claim is too vague or qualitative to operationalize. |

Do not mark a claim as `supported` just because an implementation produced a similar aggregate result. Record the artefact or calculation that supports it.
"""


def artifact_inventory() -> str:
    return """# Artefact Inventory

## Summary

| Artefact | Status | Location | Needed For | Notes |
| --- | --- | --- | --- | --- |
| Paper PDF/source | TBD | TBD | Claim extraction | TBD |
| Code repository | TBD | TBD | Direct rerun or implementation reference | TBD |
| Raw dataset | TBD | TBD | Empirical reproduction | TBD |
| Processed dataset | TBD | TBD | Validation or rerun | TBD |
| Runtime logs | TBD | TBD | Execution provenance | TBD |
| Model artefacts | TBD | TBD | Model behaviour reproduction | TBD |
| Prompts/completions | TBD | TBD | LLM decision reproduction | TBD |
| Evaluation scripts | TBD | TBD | Metric validation | TBD |
| Environment/dependencies | TBD | TBD | Rerun fidelity | TBD |

## Reproduction Consequences

- TBD
"""


def artifact_request() -> str:
    return """# Artefact Request

To independently reproduce the reported experiment, request the following from the authors or source repository.

1. Exact raw input dataset(s), including timestamps, entity identifiers, filters, and exclusions.
2. Processed datasets or scripts that generate them from raw inputs.
3. Train/validation/test splits, random seeds, and sampling rules.
4. Full configuration used for each reported run.
5. Runtime logs, audit traces, decisions, retries, and failure records.
6. Model identifiers, weights, prompts, sampling parameters, and provider/server details.
7. Evaluation scripts and benchmark construction logic.
8. Dependency versions, hardware assumptions, and external API versions.
9. Manual intervention, filtering, tuning, or post-processing records.

## Paper-Specific Additions

- TBD
"""


def validation_plan() -> str:
    return """# Validation Plan

## Goal

Validate claims that can be checked from the paper text, released artefacts, or public data. Do not conflate validation with empirical reproduction.

## Static Checks

| Claim IDs | Check | Inputs | Expected Output | Notes |
| --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD |

## Statistical Checks

| Claim IDs | Test/Statistic | Inputs | Assumptions | Notes |
| --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD |

## Public-Data Checks

| Claim IDs | Source | Coverage Needed | Smoke Test | Notes |
| --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD |

## Unsupported Claims

| Claim IDs | Missing Artefact | Consequence |
| --- | --- | --- |
| TBD | TBD | TBD |

## Planned Outputs

- validation report;
- claim-ledger status summary;
- machine-readable validation results;
- negative findings where applicable.
"""


def replication_plan() -> str:
    return """# Replication Plan

## Replication Type

Choose one or more:

- direct rerun;
- clean-room functional replication;
- public-data proxy replication;
- synthetic replication;
- component diagnostic.

Selected type: TBD

## Component Mapping

| Paper Component | Planned Implementation | Fidelity | Missing Details | Notes |
| --- | --- | --- | --- | --- |
| Input data | TBD | TBD | TBD | TBD |
| Preprocessing | TBD | TBD | TBD | TBD |
| Model/method | TBD | TBD | TBD | TBD |
| Runtime pipeline | TBD | TBD | TBD | TBD |
| Evaluation | TBD | TBD | TBD | TBD |

## Run Artefacts

- run manifest;
- input coverage report;
- pipeline or decision log;
- summary metrics;
- comparison-to-paper report;
- compact evidence bundle.

## Non-Reproduction Boundaries

- TBD
"""


def evidence_plan() -> str:
    return """# Evidence Plan

## Policy

Raw data and large generated outputs remain local by default. Commit compact evidence that is small, non-secret, and enough to audit the report.

## Local-Only Artefacts

- raw datasets;
- downloaded API data;
- full generated result directories;
- provider logs and raw model completions;
- credentials and environment files.

## Commit-Eligible Artefacts

- claim ledger;
- validation reports;
- public-data coverage summaries;
- run manifests without secrets;
- compact evidence bundles;
- final assessment.

## Evidence Bundle Requirements

- paper identity;
- command and git commit;
- input summary and checksums;
- output summary and checksums;
- limitations and missing artefacts.
"""


def evidence_bundle_template(meta: dict[str, str]) -> str:
    bundle = {
        "paper": {
            "title": meta["title"],
            "arxiv_id": meta["arxiv_id"],
            "version": meta["paper_version"],
            "url": meta["paper_url"],
        },
        "run": {
            "command": "TBD",
            "git_commit": "TBD",
            "started_at": "TBD",
            "finished_at": "TBD",
        },
        "inputs": {
            "source": "TBD",
            "rows": None,
            "entities": None,
            "coverage_summary": "TBD",
            "checksums": {},
        },
        "outputs": {
            "summary_metrics": {},
            "result_counts": {},
            "checksums": {},
        },
        "limitations": [],
    }
    return json.dumps(bundle, indent=2) + "\n"


def milestone_review() -> str:
    return """# Milestone Review

## Current Status

- Date: TBD
- Reviewer: TBD
- Git commit: TBD

## Claim-Ledger Status

| Status | Count |
| --- | ---: |
| supported | TBD |
| partially_supported | TBD |
| unsupported | TBD |
| contradicted | TBD |
| not_testable | TBD |

## Key Findings

- TBD

## Reproduction Boundary

TBD. State whether direct empirical reproduction is possible from available artefacts.

## Next Work

1. TBD
"""


def final_report_template() -> str:
    return """# Final Validation and Replication Report

## Executive Conclusion

TBD. Lead with what is supported, what is unsupported, and whether empirical reproduction is possible.

## Paper and Scope

- Title: TBD
- arXiv ID/version: TBD
- Date accessed: TBD
- Replication type: TBD

## Artefact Availability

TBD.

## Claim Validation Summary

TBD.

## Static Validation Results

TBD.

## Public-Data Reconstruction

TBD.

## Functional Replication

TBD.

## Comparison to Paper

TBD.

## Negative Findings and Contradictions

TBD.

## Evidence and Commands

TBD.

## Limitations

TBD.

## Final Assessment

TBD. Use precise language: validated, functionally replicated, proxy comparison, unsupported, or not independently reproducible.
"""


def component_readme(name: str) -> str:
    return f"""# {name}

Purpose: TBD.

Keep this directory focused. Document commands, inputs, outputs, and limitations as implementation is added.
"""


def issue_spec(title: str, goal: str, deliverables: list[str]) -> str:
    deliverable_lines = "\n".join(f"- {item}" for item in deliverables)
    return f"""# {title}

## Goal

{goal}

## Deliverables

{deliverable_lines}

## Acceptance Criteria

- Scope is explicit.
- Commands or manual review steps are documented.
- Unsupported claims or missing artefacts are recorded.
- Outputs are linked from the relevant report or plan.
"""


def issue_files() -> dict[str, str]:
    return {
        "docs/issues/01-paper-intake.md": issue_spec(
            "Paper Intake and Scope",
            "Record paper identity, headline claims, available artefacts, missing artefacts, and initial reproduction boundary.",
            [
                "completed `docs/intake/paper_intake.md`",
                "initial scope statement",
                "list of immediate reproduction blockers",
            ],
        ),
        "docs/issues/02-claim-ledger.md": issue_spec(
            "Claim Ledger Extraction",
            "Extract material claims from the paper into stable claim IDs with locations, dependencies, and planned validation methods.",
            [
                "populated `docs/claims/claim_ledger.csv`",
                "status definitions applied consistently",
                "headline claims covered",
            ],
        ),
        "docs/issues/03-static-validation.md": issue_spec(
            "Static Validation Checks",
            "Implement and test arithmetic or statistical checks that can be recomputed from available materials.",
            [
                "validation formulas documented",
                "tests for implemented checks",
                "validation report draft",
            ],
        ),
        "docs/issues/04-data-smoke.md": issue_spec(
            "Data Availability Smoke Test",
            "Verify whether public or released data sources can support the required paper window, entities, schema, and granularity.",
            [
                "small smoke fetch or manual availability check",
                "coverage notes",
                "fallback/proxy decision if needed",
            ],
        ),
        "docs/issues/05-replication-skeleton.md": issue_spec(
            "Replication Skeleton",
            "Create the smallest auditable implementation that maps paper components to runnable code.",
            [
                "component mapping completed",
                "tiny synthetic or fixture run",
                "pipeline outputs defined",
            ],
        ),
        "docs/issues/06-evidence-bundle.md": issue_spec(
            "Compact Evidence Bundle",
            "Create small non-secret evidence bundles that summarize inputs, outputs, commands, checksums, and limitations.",
            [
                "evidence bundle generated",
                "large local artefacts excluded from git",
                "evidence linked from reports",
            ],
        ),
        "docs/issues/07-final-assessment.md": issue_spec(
            "Final Assessment",
            "Write the final report with supported claims, unsupported claims, negative findings, evidence links, and reproduction boundary.",
            [
                "final report completed",
                "claim statuses summarized",
                "missing author artefacts listed",
            ],
        ),
    }


def ci_files() -> dict[str, str]:
    return {
        ".github/workflows/validation-smoke.yml": """name: validation-smoke

on:
  pull_request:
  workflow_dispatch:

jobs:
  smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Check for large committed files
        run: |
          python - <<'PY'
          from pathlib import Path
          limit = 5 * 1024 * 1024
          ignored = {'.git'}
          too_large = []
          for path in Path('.').rglob('*'):
              if not path.is_file() or any(part in ignored for part in path.parts):
                  continue
              if path.stat().st_size > limit:
                  too_large.append(f'{path} ({path.stat().st_size} bytes)')
          if too_large:
              raise SystemExit('Large files detected:\n' + '\n'.join(too_large))
          PY
      - name: Run tests when present
        run: |
          if [ -d tests ]; then
            python -m pip install pytest
            pytest tests -q
          else
            echo "No tests directory present"
          fi
      - name: Basic Markdown link sanity
        run: |
          python - <<'PY'
          from pathlib import Path
          import re
          missing = []
          pattern = re.compile(r'\\[[^\\]]+\\]\\((?!https?://|mailto:|#)([^)]+)\\)')
          for md in Path('.').rglob('*.md'):
              if '.git' in md.parts:
                  continue
              for match in pattern.finditer(md.read_text(encoding='utf-8')):
                  target = match.group(1).split('#', 1)[0]
                  if not target:
                      continue
                  if not (md.parent / target).resolve().exists():
                      missing.append(f'{md}: {target}')
          if missing:
              raise SystemExit('Missing Markdown links:\n' + '\n'.join(missing))
          PY
"""
    }


def base_files(meta: dict[str, str]) -> dict[str, str]:
    return {
        "README.md": readme(meta),
        ".gitignore": gitignore(),
        "docs/intake/paper_intake.md": intake(meta),
        "docs/claims/claim_ledger.csv": claim_ledger(),
        "docs/claims/claim_status_guide.md": claim_status_guide(),
        "docs/artifacts/artifact_inventory.md": artifact_inventory(),
        "docs/artifacts/artifact_request.md": artifact_request(),
        "docs/validation/validation_plan.md": validation_plan(),
        "docs/replication/replication_plan.md": replication_plan(),
        "docs/evidence/evidence_plan.md": evidence_plan(),
        "docs/evidence/evidence_bundle_template.json": evidence_bundle_template(meta),
        "docs/reports/milestone_review.md": milestone_review(),
        "docs/reports/final_report_template.md": final_report_template(),
        "validation/README.md": component_readme("Validation"),
        "replication/README.md": component_readme("Replication"),
        "scripts/README.md": component_readme("Scripts"),
        "tests/README.md": component_readme("Tests"),
    }


def apply_template_overrides(
    generated_files: dict[str, str], template_dir: Path | None
) -> dict[str, str]:
    if template_dir is None:
        return generated_files
    if not template_dir.exists() or not template_dir.is_dir():
        raise SystemExit(f"Template directory does not exist: {template_dir}")

    template_targets = {
        "claim_ledger.csv": "docs/claims/claim_ledger.csv",
        "artifact_inventory.md": "docs/artifacts/artifact_inventory.md",
        "validation_plan.md": "docs/validation/validation_plan.md",
        "replication_plan.md": "docs/replication/replication_plan.md",
        "final_report.md": "docs/reports/final_report_template.md",
    }

    for template_name, target in template_targets.items():
        template_path = template_dir / template_name
        if template_path.exists():
            generated_files[target] = template_path.read_text(encoding="utf-8")
    return generated_files


def files(
    meta: dict[str, str],
    with_issues: bool,
    with_ci: bool,
    template_dir: Path | None,
) -> dict[str, str]:
    generated_files = apply_template_overrides(base_files(meta), template_dir)
    if with_issues:
        generated_files.update(issue_files())
    if with_ci:
        generated_files.update(ci_files())
    return generated_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a starter workspace for arXiv paper validation and replication."
    )
    parser.add_argument("--project-dir", required=True, help="Directory to create or populate.")
    parser.add_argument("--title", required=True, help="Paper title.")
    parser.add_argument("--arxiv-id", required=True, help="arXiv identifier, for example 2501.01234.")
    parser.add_argument("--paper-version", default="v1", help="Paper version, default: v1.")
    parser.add_argument("--paper-url", default="", help="Paper URL.")
    parser.add_argument("--authors", default="", help="Semicolon-separated author list.")
    parser.add_argument("--field", default="", help="Research field or domain.")
    parser.add_argument("--task", default="", help="Main validation or replication task.")
    parser.add_argument(
        "--with-issues",
        action="store_true",
        help="Generate starter issue-spec Markdown files under docs/issues/.",
    )
    parser.add_argument(
        "--with-ci",
        action="store_true",
        help="Generate a minimal GitHub Actions smoke workflow.",
    )
    parser.add_argument(
        "--template-dir",
        default="",
        help="Optional directory containing template overrides by filename.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow writing into a non-empty directory and overwriting generated files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()

    if project_dir.exists() and any(project_dir.iterdir()) and not args.force:
        raise SystemExit(
            f"Refusing to populate non-empty directory without --force: {project_dir}"
        )

    project_dir.mkdir(parents=True, exist_ok=True)
    meta = metadata(args)
    template_dir = Path(args.template_dir).expanduser().resolve() if args.template_dir else None

    for relative_path, content in files(
        meta,
        with_issues=args.with_issues,
        with_ci=args.with_ci,
        template_dir=template_dir,
    ).items():
        write_file(project_dir / relative_path, content, args.force)

    print(f"Created paper validation scaffold: {project_dir}")
    print("Next steps:")
    print("1. Fill docs/intake/paper_intake.md")
    print("2. Populate docs/claims/claim_ledger.csv")
    print("3. Complete docs/artifacts/artifact_inventory.md")
    print("4. Decide validation and replication scope before implementation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
