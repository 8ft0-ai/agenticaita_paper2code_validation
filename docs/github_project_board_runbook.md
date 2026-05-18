# GitHub Project Board Runbook

Issue #32 requires a GitHub Project board for the replication roadmap. Creating the board requires GitHub Projects permissions that are not available to the current automation token, so this runbook records the intended board shape and the commands to run once a token with `read:project` and project write permissions is available.

This document is not a substitute for the Project itself. It is a reproducible setup guide and acceptance checklist for the blocked Project-creation step.

## Intended board

Use a GitHub Projects v2 board attached to the repository or owning account.

Recommended name:

```text
AGENTICAITA replication roadmap
```

Recommended status values:

```text
Backlog
Ready
In Progress
In Review
Done
Blocked / Needs Artefacts
```

Recommended custom fields:

| Field | Type | Values |
| --- | --- | --- |
| `Area` | Single select | `validation`, `replication`, `data`, `docs` |
| `Priority` | Single select | `P0`, `P1`, `P2` |
| `Evidence Level` | Single select | `static audit`, `functional replication`, `empirical replication` |
| `Artifact Dependency` | Single select | `none`, `public data`, `author artefacts required` |

## Issues to add

Add the roadmap issues named in #32:

```text
#21
#22
#23
#24
#25
#26
#27
#28
#29
#30
#31
```

Also add any later follow-up roadmap issues when they replace or extend the original issue range.

## Permission check

Run this first with the intended GitHub token:

```bash
gh auth status
gh project list --owner 8ft0-ai
```

If `gh project list` reports that `read:project` is required, re-authorise the token with the required Projects scopes before attempting board creation.

## Setup procedure

Create the board:

```bash
gh project create --owner 8ft0-ai --title "AGENTICAITA replication roadmap"
```

Capture the project number from the command output, then add the issues:

```bash
PROJECT_NUMBER=<project-number>
REPO=8ft0-ai/agenticaita_paper2code_validation

for issue in 21 22 23 24 25 26 27 28 29 30 31; do
  gh project item-add "$PROJECT_NUMBER" --owner 8ft0-ai --url "https://github.com/$REPO/issues/$issue"
done
```

Create the custom fields in the Projects web UI if the local `gh` version does not expose field-creation commands. After fields exist, set values for each item according to the issue labels and evidence level implied by the issue body.

Suggested defaults:

| Issue area | Area | Evidence Level | Artifact Dependency |
| --- | --- | --- | --- |
