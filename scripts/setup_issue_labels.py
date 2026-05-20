#!/usr/bin/env python3
"""Create or update the repository issue-label taxonomy."""
from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class LabelSpec:
    name: str
    color: str
    description: str


LABELS: tuple[LabelSpec, ...] = (
    LabelSpec("area:validation", "1f77b4", "Static and real-data claim validation."),
    LabelSpec("area:replication", "5319e7", "Functional replication harness and architecture runs."),
    LabelSpec("area:data", "0e8a16", "Market-data download, conversion, coverage, or storage workflows."),
    LabelSpec("area:docs", "0075ca", "Repository docs, Wiki staging pages, runbooks, and evidence pages."),
    LabelSpec("area:automation", "c5def5", "Scripts, Actions, broker tooling, issue management, and CI automation."),
    LabelSpec("area:workflow", "bfdadc", "Repository process, patch-submission flow, and operating model changes."),
    LabelSpec("area:research", "d4c5f9", "Open research questions or exploratory investigations."),
    LabelSpec("priority:P0", "b60205", "Urgent or blocks the current roadmap."),
    LabelSpec("priority:P1", "d93f0b", "Important and should be done soon."),
    LabelSpec("priority:P2", "fbca04", "Useful, but can wait."),
    LabelSpec("status:backlog", "ededed", "Captured but not ready for work."),
    LabelSpec("status:ready", "0e8a16", "Clear enough to start."),
    LabelSpec("status:in-progress", "fbca04", "Someone or an agent is actively working on it."),
    LabelSpec("status:review", "5319e7", "Implemented and awaiting PR, review, or merge."),
    LabelSpec("status:blocked", "b60205", "Cannot proceed without a dependency or human action."),
    LabelSpec("status:done", "c2e0c6", "Completed and retained for dashboard history if useful."),
    LabelSpec("size:small", "c2e0c6", "Suitable for one focused patch or PR."),
    LabelSpec("size:medium", "fbca04", "Manageable, but likely touches multiple files or behaviours."),
    LabelSpec("size:large", "d93f0b", "Should usually be split before an agent starts work."),
    LabelSpec("evidence:static-audit", "c5def5", "Checks reported quantities, logic, or documentation without live reconstruction."),
    LabelSpec("evidence:functional-replication", "d4c5f9", "Executes a functional approximation of the paper architecture."),
    LabelSpec("evidence:empirical-replication", "5319e7", "Uses public market data for comparable empirical reconstruction."),
    LabelSpec("artifact:none", "c2e0c6", "No special external artefacts are required."),
    LabelSpec("artifact:public-data", "0e8a16", "Public data must be fetched or available locally."),
    LabelSpec("artifact:author-artifacts-required", "b60205", "Depends on unavailable original paper artefacts."),
    LabelSpec("agent-ready", "0e8a16", "Safe for an assistant to pick up without further clarification."),
    LabelSpec("needs-human", "d93f0b", "Requires a human decision or manual action."),
    LabelSpec("needs-triage", "fbca04", "Missing area, priority, status, or scope metadata."),
    LabelSpec("needs-acceptance-criteria", "d93f0b", "The issue is not specific enough to implement safely."),
    LabelSpec("blocked:credentials", "b60205", "Requires a token, secret, account permission, or external credential."),
    LabelSpec("blocked:external-api", "b60205", "Blocked by an external API or service behaviour."),
    LabelSpec("blocked:manual-step", "b60205", "Requires a manual step outside repository automation."),
    LabelSpec("blocked:author-artifacts", "b60205", "Requires original paper artefacts not present in the repository."),
)


def run(command: list[str], *, dry_run: bool) -> None:
    print("+ " + " ".join(command))
    if not dry_run:
        subprocess.run(command, check=True)


def label_exists(repo: str, name: str) -> bool:
    result = subprocess.run(
        ["gh", "label", "list", "--repo", repo, "--search", name, "--json", "name", "--jq", ".[].name"],
        check=True,
        capture_output=True,
        text=True,
    )
    return name in {line.strip() for line in result.stdout.splitlines()}


def apply_label(repo: str, label: LabelSpec, *, dry_run: bool) -> None:
    base = ["gh", "label"]
    if label_exists(repo, label.name):
        command = [
            *base,
            "edit",
            label.name,
            "--repo",
            repo,
            "--color",
            label.color,
            "--description",
            label.description,
        ]
    else:
        command = [
            *base,
            "create",
            label.name,
            "--repo",
            repo,
            "--color",
            label.color,
            "--description",
            label.description,
        ]
    run(command, dry_run=dry_run)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Repository in owner/name form.")
    parser.add_argument("--dry-run", action="store_true", help="Print gh commands without applying label changes.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    for label in LABELS:
        apply_label(args.repo, label, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
