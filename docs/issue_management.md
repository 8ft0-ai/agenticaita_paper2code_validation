# Issue-Native Development Management

This repository uses GitHub issues as the canonical planning surface for validation, replication, documentation, and workflow work. GitHub Projects may still be useful as a human visual board, but the repository should not depend on Project-board state for agentic development.

The operating rule is:

> Issues are the work items, labels are the workflow fields, milestones are the planning horizons, and repository documentation is the durable roadmap.

## Why this model

The current GitHub connector can reliably inspect repository files, issues, pull requests, labels attached to issues, and Actions logs. It cannot reliably inspect GitHub Projects v2 boards. Keeping planning state in issue metadata makes the work visible to humans, GitHub Actions, and assistant-driven development sessions.

## Label families

Labels use prefixes so they behave like structured fields.

### Area

Use one primary `area:*` label where possible.

| Label | Meaning |
| --- | --- |
| `area:validation` | Static and real-data claim validation. |
| `area:replication` | Functional replication harness and architecture runs. |
| `area:data` | Market-data download, conversion, coverage, or storage workflows. |
| `area:docs` | Repository docs, Wiki staging pages, runbooks, and evidence pages. |
| `area:automation` | Scripts, Actions, broker tooling, issue management, and CI automation. |
| `area:workflow` | Repository process, patch-submission flow, and operating model changes. |
| `area:research` | Open research questions or exploratory investigations. |

### Priority

Priority labels are local to this repository.

| Label | Meaning |
| --- | --- |
| `priority:P0` | Urgent or blocks the current roadmap. |
| `priority:P1` | Important and should be done soon. |
| `priority:P2` | Useful, but can wait. |

### Status

Use one `status:*` label at a time.

| Label | Meaning |
| --- | --- |
| `status:backlog` | Captured but not ready for work. |
| `status:ready` | Clear enough to start. |
| `status:in-progress` | Someone or an agent is actively working on it. |
| `status:review` | Implemented and awaiting PR/review/merge. |
| `status:blocked` | Cannot proceed without a dependency or human action. |
| `status:done` | Completed and retained for issue-dashboard history if useful. |

### Size

| Label | Meaning |
| --- | --- |
| `size:small` | Suitable for one focused patch or PR. |
| `size:medium` | Manageable, but likely touches multiple files or behaviours. |
| `size:large` | Should usually be split before an agent starts work. |

### Evidence level

| Label | Meaning |
| --- | --- |
| `evidence:static-audit` | Checks reported quantities, logic, or documentation without live reconstruction. |
| `evidence:functional-replication` | Executes a functional approximation of the paper architecture. |
| `evidence:empirical-replication` | Uses public market data for comparable empirical reconstruction. |

### Artifact dependency

| Label | Meaning |
| --- | --- |
| `artifact:none` | No special external artefacts are required. |
| `artifact:public-data` | Public data must be fetched or available locally. |
| `artifact:author-artifacts-required` | The issue depends on unavailable original paper artefacts. |

### Agent workflow

| Label | Meaning |
| --- | --- |
| `agent-ready` | Safe for an assistant to pick up without further clarification. |
| `needs-human` | Requires a human decision or manual action. |
| `needs-triage` | Missing area, priority, status, or scope metadata. |
| `needs-acceptance-criteria` | The issue is not specific enough to implement safely. |
| `blocked:credentials` | Requires a token, secret, account permission, or external credential. |
| `blocked:external-api` | Blocked by an external API or service behaviour. |
| `blocked:manual-step` | Requires a manual step outside repository automation. |
| `blocked:author-artifacts` | Requires original paper artefacts not present in the repository. |

## `agent-ready` definition

Only apply `agent-ready` when all of these are true:

- the goal is clear;
- the change is scoped to one issue;
- acceptance criteria are explicit;
- expected validation is stated;
- relevant files, directories, or commands are identified;
- the issue is not blocked by credentials, missing artefacts, or a manual external step;
- generated artefact and retention constraints are clear;
- the likely change is `size:small` or a clearly bounded `size:medium`.

Do not combine `agent-ready` with `status:blocked`, `needs-human`, or `needs-acceptance-criteria`.

## Suggested assistant selection rule

When asked to take the next issue, an assistant should prefer:

1. open issues with `agent-ready`;
2. `priority:P0`, then `priority:P1`, then `priority:P2`;
3. `size:small` before `size:medium`;
4. issues that are not blocked and have a clear validation path.

The assistant should work on exactly one issue and submit through the patch-submission broker described in `AGENTS.md`.

## Label setup

Run the label setup script from the repository root:

```bash
python scripts/setup_issue_labels.py --repo 8ft0-ai/agenticaita_paper2code_validation --dry-run
python scripts/setup_issue_labels.py --repo 8ft0-ai/agenticaita_paper2code_validation
```

The script shells out to the GitHub CLI. It is intentionally small and safe to inspect. Use `--dry-run` before applying changes.

## Future extensions

The next issue-management improvements should add:

- issue forms under `.github/ISSUE_TEMPLATE/`;
- a roadmap document under `docs/roadmap.md`;
- an issue-dashboard generator that groups open issues by labels, priority, milestone, and blocked state;
- a report-only issue hygiene workflow that detects contradictory or missing metadata.
