#!/usr/bin/env python3
"""Create a lightweight, auditable paper-validation project scaffold."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

SCAFFOLD_VERSION = "2.0"
MODERN_ARXIV_ID = re.compile(r"^\d{4}\.\d{4,5}$")
LEGACY_ARXIV_ID = re.compile(r"^[a-z-]+(?:\.[A-Z]{2})?/\d{7}$", re.IGNORECASE)
PAPER_VERSION = re.compile(r"^v[1-9]\d*$", re.IGNORECASE)

TEMPLATE_TARGETS = {
    "claim_ledger.csv": "docs/claims/claim_ledger.csv",
    "artifact_inventory.md": "docs/artifacts/artifact_inventory.md",
    "validation_plan.md": "docs/validation/validation_plan.md",
    "replication_plan.md": "docs/replication/replication_plan.md",
    "final_report.md": "docs/reports/final_report_template.md",
}


@dataclass(frozen=True)
class Options:
    project_dir: Path
    title: str
    arxiv_id: str
    paper_version: str
    paper_url: str
    authors: str
    field: str
    task: str
    template_dir: Path
    with_issue_specs: bool
    with_ci: bool
    dry_run: bool
    update_missing: bool
    force: bool


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value or "paper-validation"


def validate_arxiv_id(value: str) -> str:
    value = value.strip()
    if not (MODERN_ARXIV_ID.fullmatch(value) or LEGACY_ARXIV_ID.fullmatch(value)):
        raise argparse.ArgumentTypeError(
            "arXiv ID must look like 2501.01234 or hep-th/9901001"
        )
    return value


def validate_paper_version(value: str) -> str:
    value = value.strip().lower()
    if not PAPER_VERSION.fullmatch(value):
        raise argparse.ArgumentTypeError("paper version must look like v1, v2, ...")
    return value


def metadata(opts: Options) -> dict[str, str]:
    return {
        "title": opts.title,
        "slug": slugify(opts.title),
        "arxiv_id": opts.arxiv_id,
        "paper_version": opts.paper_version,
        "paper_url": opts.paper_url or f"https://arxiv.org/abs/{opts.arxiv_id}",
        "authors": opts.authors or "TBD",
        "field": opts.field or "TBD",
        "task": opts.task or "TBD",
        "created": date.today().isoformat(),
        "scaffold_version": SCAFFOLD_VERSION,
    }


def render(content: str, meta: dict[str, str]) -> str:
    for key, value in meta.items():
        content = content.replace("{{" + key.upper() + "}}", value)
    return content


def read_templates(template_dir: Path, meta: dict[str, str]) -> dict[str, str]:
    if not template_dir.is_dir():
        raise SystemExit(f"Template directory does not exist: {template_dir}")
    generated: dict[str, str] = {}
    missing: list[str] = []
    for name, target in TEMPLATE_TARGETS.items():
        path = template_dir / name
        if not path.is_file():
            missing.append(name)
            continue
        generated[target] = render(path.read_text(encoding="utf-8"), meta)
    if missing:
        raise SystemExit("Missing required templates: " + ", ".join(sorted(missing)))
    return generated


def project_readme(meta: dict[str, str]) -> str:
    return f"""# {meta['title']} Validation and Replication

Created: {meta['created']}  
Scaffold: v{meta['scaffold_version']}

| Field | Value |
| --- | --- |
| Paper | {meta['title']} |
| arXiv ID | {meta['arxiv_id']} |
| Version | {meta['paper_version']} |
| URL | {meta['paper_url']} |
| Authors | {meta['authors']} |
| Field | {meta['field']} |
| Task | {meta['task']} |

## Current scope

Complete `docs/intake/paper_intake.md` and Gate A before implementation expands. The default scope supports static validation, artefact audit, public-data reconstruction, and functional replication. It does not support an empirical-reproduction claim without the original code/data/evaluation path and materially equivalent runtime context.

## Start here

1. `docs/intake/paper_intake.md`
2. `docs/claims/claim_ledger.csv`
3. `docs/artifacts/artifact_inventory.md`
4. `docs/governance/data_and_licensing.md`
5. `docs/decisions/gate_log.md`
6. `docs/validation/validation_plan.md`
7. `docs/replication/replication_plan.md`
8. `docs/review/final_independent_review.md`
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

# Notebooks and local scratch
.ipynb_checkpoints/
scratch/
tmp/
"""


def intake(meta: dict[str, str]) -> str:
    return f"""# Paper Intake

Date created: {meta['created']}

## Paper identity

| Field | Value |
| --- | --- |
| Title | {meta['title']} |
| arXiv ID | {meta['arxiv_id']} |
| Frozen version | {meta['paper_version']} |
| URL | {meta['paper_url']} |
| Authors | {meta['authors']} |
| Date accessed | TBD |

## Headline claims

| Claim | Importance | Why it matters |
| --- | --- | --- |
| TBD | headline/supporting/contextual | TBD |

## Released and missing artefacts

- Released: TBD
- Missing: TBD

## Initial scope and stopping rules

- Selected project type: TBD
- What would change the final conclusion: TBD
- Conditions that stop direct reproduction: TBD
- Conditions that justify functional/proxy work: TBD
"""


def claim_status_guide() -> str:
    return """# Claim Status Guide

Use `unreviewed`, `supported`, `partially_supported`, `unsupported`, `contradicted`, or `not_testable`.

A supported claim must cite evidence or a reproducible calculation. Similar aggregate output from a different implementation is not sufficient. Record extraction method and confidence separately from claim status.
"""


def artifact_request() -> str:
    return """# Artefact Request

Request only artefacts material to the prioritised claims:

1. exact raw and processed inputs, filters, exclusions, and splits;
2. original code and evaluation scripts;
3. configuration, seeds, dependency lockfiles, container images, and hardware assumptions;
4. runtime logs, checkpoints, traces, retries, failures, and manual interventions;
5. model identifiers, weights, prompts, completions, provider versions, and tool context;
6. benchmark construction and post-processing logic;
7. licence, redistribution, and retention constraints.

## Paper-specific request

- TBD
"""


def project_profile() -> str:
    return """# Project Profile

Repository-specific instructions belong here rather than in the universal playbook.

## Runtime and dependencies

- Runtime version: TBD
- Dependency install/lock command: TBD
- Container image/digest: TBD
- Hardware requirements: TBD

## Validation commands

- Static validation: TBD
- Unit tests: TBD
- Documentation/link checks: TBD
- Smoke run: TBD

## Contribution workflow

- Branch/PR or broker process: TBD
- Generated-output exclusions: `data/`, `results/`, `outputs/`
- Required credentials and secret names: TBD
"""


def governance_files() -> dict[str, str]:
    return {
        "docs/governance/data_and_licensing.md": """# Data and Licensing Decision

Complete before bulk collection or redistribution.

| Question | Decision | Evidence/owner |
| --- | --- | --- |
| Dataset licence permits intended use | TBD | TBD |
| Redistribution or sample commitment permitted | TBD | TBD |
| API terms and scraping restrictions reviewed | TBD | TBD |
| Personal/sensitive data present | TBD | TBD |
| Provider/model output retention restrictions reviewed | TBD | TBD |
| External artefact retention owner and expiry | TBD | TBD |

Gate result: `pending`.
""",
        "docs/governance/retention_policy.md": """# Retention Policy

Raw datasets, large outputs, provider logs, secrets, and local databases remain outside git by default. Commit code, plans, claim ledgers, compact manifests/evidence, small fixtures, and reviewed reports. Record external storage location, owner, checksum, and retention period when raw evidence is retained elsewhere.
""",
        "docs/decisions/gate_log.md": """# Decision Gate Log

| Gate | Decision | Date | Evidence | Reviewer | Consequence |
| --- | --- | --- | --- | --- | --- |
| A — scope and artefacts | pending | TBD | TBD | TBD | TBD |
| B — data/legal adequacy | pending | TBD | TBD | TBD | TBD |
| C — claim and metric definition | pending | TBD | TBD | TBD | TBD |
| D — implementation value | pending | TBD | TBD | TBD | TBD |
| E — expensive run readiness | pending | TBD | TBD | TBD | TBD |
| F — final independent review | pending | TBD | TBD | TBD | TBD |
""",
        "docs/versions/paper_version_log.md": """# Paper Version Log

Freeze each milestone against one paper version. Do not silently replace claims when a new version appears.

| Version | Accessed | Changes affecting claims | Action |
| --- | --- | --- | --- |
| TBD | TBD | Initial frozen version | Establish claim ledger |
""",
        "docs/review/final_independent_review.md": """# Final Independent Review

Reviewer should work from a clean context and verify:

- paper locations and extracted values;
- formulas, denominators, exclusions, and benchmark definitions;
- claim statuses and evidence references;
- environment and run provenance;
- unsupported inferences and proxy/reproduction language;
- agreement between generated evidence and narrative reports.

Decision: `pending`.
""",
    }


def component_readme(name: str) -> str:
    return f"# {name}\n\nPurpose, commands, inputs, outputs, and limitations: TBD.\n"


def issue_spec(title: str, goal: str) -> str:
    return f"""# {title}

## Goal

{goal}

## Acceptance criteria

- linked claim IDs and priority are explicit;
- commands or review steps are documented;
- evidence and limitations are recorded;
- stopping condition is stated;
- outputs are linked from the relevant plan or report.
"""


def issue_files() -> dict[str, str]:
    specs = [
        ("01-intake-and-gate-a.md", "Paper intake and Gate A", "Freeze the paper version, prioritise headline claims, inventory artefacts, and decide the reproduction boundary."),
        ("02-claim-ledger.md", "Prioritised claim ledger", "Extract material claims with importance, validation priority, extraction confidence, dependencies, and evidence references."),
        ("03-static-validation.md", "Static validation", "Implement and test all high-priority arithmetic and statistical checks that available materials permit."),
        ("04-data-and-legal-smoke.md", "Data and legal smoke", "Verify coverage, licence, retention, schema, rate limits, and redistribution constraints before bulk acquisition."),
        ("05-replication-skeleton.md", "Minimal replication skeleton", "Implement the smallest auditable system needed to exercise the prioritised claim boundary."),
        ("06-evidence-bundle.md", "Compact evidence bundle", "Capture environment, inputs, outputs, hashes, limitations, and local-only artefacts without secrets."),
        ("07-independent-review.md", "Independent final review", "Check extraction, calculations, statuses, evidence, and final language from a clean context."),
    ]
    return {f"docs/issues/{path}": issue_spec(title, goal) for path, title, goal in specs}


def ci_workflow() -> str:
    return """name: validation-smoke

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
      - name: Check for unexpectedly large committed files
        run: |
          python - <<'PY'
          from pathlib import Path
          limit = 5 * 1024 * 1024
          bad = [str(p) for p in Path('.').rglob('*') if p.is_file() and '.git' not in p.parts and p.stat().st_size > limit]
          if bad:
              raise SystemExit('Large files detected:\n' + '\n'.join(bad))
          PY
      - name: Run tests when Python tests exist
        run: |
          if find tests -type f -name 'test_*.py' -print -quit | grep -q .; then
            python -m pip install pytest
            python -m pytest tests -q
          else
            echo 'No Python tests present yet'
          fi
      - name: Basic relative Markdown link check
        run: |
          python - <<'PY'
          from pathlib import Path
          import re
          missing = []
          pattern = re.compile(r'\\[[^\\]]+\\]\\((?!https?://|mailto:|#)([^)]+)\\)')
          for md in Path('.').rglob('*.md'):
              if '.git' in md.parts:
                  continue
              text = md.read_text(encoding='utf-8')
              for target in pattern.findall(text):
                  clean = target.split('#', 1)[0]
                  if clean and not (md.parent / clean).resolve().exists():
                      missing.append(f'{md}: {target}')
          if missing:
              raise SystemExit('Missing Markdown links:\n' + '\n'.join(missing))
          PY
"""


def base_files(meta: dict[str, str], templates: dict[str, str]) -> dict[str, str]:
    files = {
        "README.md": project_readme(meta),
        ".gitignore": gitignore(),
        "PROJECT_PROFILE.md": project_profile(),
        "docs/intake/paper_intake.md": intake(meta),
        "docs/claims/claim_status_guide.md": claim_status_guide(),
        "docs/artifacts/artifact_request.md": artifact_request(),
        "validation/README.md": component_readme("Validation"),
        "replication/README.md": component_readme("Replication"),
        "scripts/README.md": component_readme("Scripts"),
        "tests/README.md": component_readme("Tests"),
    }
    files.update(governance_files())
    files.update(templates)
    return files


def scaffold_files(opts: Options) -> tuple[dict[str, str], dict[str, str]]:
    meta = metadata(opts)
    templates = read_templates(opts.template_dir, meta)
    files = base_files(meta, templates)
    if opts.with_issue_specs:
        files.update(issue_files())
    if opts.with_ci:
        files[".github/workflows/validation-smoke.yml"] = ci_workflow()
    manifest = {
        "scaffold_version": SCAFFOLD_VERSION,
        "paper": {k: meta[k] for k in ("title", "arxiv_id", "paper_version", "paper_url")},
        "generated_files": sorted(files),
    }
    files[".paper-validation-scaffold.json"] = json.dumps(manifest, indent=2) + "\n"
    return files, meta


def write_plan(project_dir: Path, files: dict[str, str], *, update_missing: bool, force: bool) -> list[tuple[Path, str]]:
    existing_nonempty = project_dir.exists() and any(project_dir.iterdir())
    if existing_nonempty and not (update_missing or force):
        raise SystemExit(f"Refusing to populate non-empty directory: {project_dir}")
    plan: list[tuple[Path, str]] = []
    for relative, content in files.items():
        target = project_dir / relative
        if target.exists() and not force:
            if update_missing:
                continue
            raise SystemExit(f"Refusing to overwrite existing file: {target}")
        plan.append((target, content))
    return plan


def apply_plan(plan: Iterable[tuple[Path, str]]) -> None:
    for path, content in plan:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--arxiv-id", required=True, type=validate_arxiv_id)
    parser.add_argument("--paper-version", required=True, type=validate_paper_version)
    parser.add_argument("--paper-url", default="")
    parser.add_argument("--authors", default="")
    parser.add_argument("--field", default="")
    parser.add_argument("--task", default="")
    parser.add_argument("--template-dir", default="")
    parser.add_argument("--with-issue-specs", action="store_true")
    parser.add_argument("--with-issues", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--with-ci", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--update-missing", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.update_missing and args.force:
        parser.error("--update-missing and --force are mutually exclusive")
    return args


def options_from_args(args: argparse.Namespace) -> Options:
    script_templates = Path(__file__).resolve().parent / "templates"
    template_dir = Path(args.template_dir).expanduser().resolve() if args.template_dir else script_templates
    return Options(
        project_dir=Path(args.project_dir).expanduser().resolve(),
        title=args.title.strip(),
        arxiv_id=args.arxiv_id,
        paper_version=args.paper_version,
        paper_url=args.paper_url.strip(),
        authors=args.authors.strip(),
        field=args.field.strip(),
        task=args.task.strip(),
        template_dir=template_dir,
        with_issue_specs=bool(args.with_issue_specs or args.with_issues),
        with_ci=bool(args.with_ci),
        dry_run=bool(args.dry_run),
        update_missing=bool(args.update_missing),
        force=bool(args.force),
    )


def main(argv: list[str] | None = None) -> int:
    opts = options_from_args(parse_args(argv))
    files, _ = scaffold_files(opts)
    plan = write_plan(opts.project_dir, files, update_missing=opts.update_missing, force=opts.force)
    if opts.dry_run:
        print("Planned files:")
        for path, _ in plan:
            print(path.relative_to(opts.project_dir))
        return 0
    opts.project_dir.mkdir(parents=True, exist_ok=True)
    apply_plan(plan)
    print(f"Created paper validation scaffold: {opts.project_dir}")
    print("Next: complete intake, claim priorities, artefact/legal audit, and Gate A before implementation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
