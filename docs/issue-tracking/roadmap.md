# Roadmap

This roadmap is the human-readable planning index for the repository. It replaces GitHub Projects as the durable planning view that can be inspected through repository files, GitHub issues, pull requests, and assistant-driven development sessions.

The source of truth remains GitHub issues and labels. This document is a curated index that points to the relevant work, explains the current direction, and helps humans and agents choose the next sensible task.

## Operating model

- Issues are the work items.
- Labels are the workflow fields.
- Milestones are the planning horizons.
- `agent-ready` marks work that an assistant can safely pick up without further clarification.
- Pull requests and patch-submission broker archives provide the implementation audit trail.

See `docs/issue_management.md` for the label taxonomy and readiness rules. See `docs/issue_dashboard_runbook.md` for the generated dashboard workflow.

## Now

Current focus: make issue-native development management practical enough to replace the GitHub Project board for day-to-day work.

| Issue | Status | Notes |
| --- | --- | --- |
| #80 Add issue dashboard runbook and roadmap links | In progress | Documents how to run and interpret the generated dashboard alongside this curated roadmap. |

## Next

These are the next high-value implementation steps after the roadmap is merged.

| Candidate issue | Area | Why it matters |
| --- | --- | --- |
| Add report-only issue hygiene checks | automation | Uses dashboard metadata warnings to detect missing labels, conflicting status labels, blocked-but-agent-ready issues, and missing acceptance criteria without mutating issues initially. |
| Decide dashboard publication policy | workflow | Determines whether generated `docs/issue_dashboard.md` and `docs/issue_dashboard.json` should remain local, be stored as Actions artefacts, or be committed by explicit snapshot issues. |
| Add roadmap-to-Wiki staging page | docs | Mirrors the curated roadmap into `docs/wiki/` so the GitHub Wiki can show the planning index. |
| Run or automate label setup | workflow | Ensures all labels referenced by issue forms and `docs/issue_management.md` exist in the repository. |

## Later

These items are useful once the core issue-native workflow is stable.

| Theme | Description |
| --- | --- |
| Auto-triage suggestions | Suggest `area:*`, `priority:*`, `size:*`, and `agent-ready` candidates from issue-form content. |
| Dashboard publication | Publish generated issue-dashboard snapshots to `docs/` or Actions artefacts. |
| Milestone hygiene | Check that accepted roadmap issues are assigned to a milestone when appropriate. |
| Closed-issue summaries | Periodically summarise completed work into the Wiki evidence and roadmap pages. |

## Blocked

Use this section for visible planning blockers. The issue labels remain the source of truth for blocked work.

| Issue | Blocker | Resolution path |
| --- | --- | --- |
| #32 Set up GitHub Project board for replication roadmap | GitHub Projects are not directly visible through the current connector context. | Treat the Project board as optional and keep canonical planning state in issues, labels, milestones, and this roadmap. |

## Done

Completed work that established the current issue-native workflow.

| Issue or PR | Result |
| --- | --- |
| #72 Define issue-native label taxonomy and setup script | Added `docs/issue_management.md` and `scripts/setup_issue_labels.py`. |
| #74 Add structured issue forms for issue-native workflow | Added structured issue forms for bugs, validation, replication, docs, automation, and research. |
| #76 Add issue-native roadmap document | Added this curated planning index as a Project-board replacement. |
| #78 Design issue dashboard schema and grouping rules | Added `docs/issue_dashboard_design.md`. |
| #79 Implement issue dashboard generator CLI | Added `scripts/generate_issue_dashboard.py`. |
| #66 Add GitHub Actions workflow to sync docs/wiki to repository Wiki | Added Wiki publication from reviewed `docs/wiki/` pages. |
| #70 Clarify Wiki sync first-run seeding requirement | Documented the one-time Wiki UI seed step. |

## Maintenance rules

- Keep this document short and curated.
- Do not duplicate full issue bodies here.
- Use this page to explain sequencing, not to replace labels or milestones.
- Move active work from `Next` to `Now` only when it is ready to be implemented.
- Mark blocked work in issues first, then summarise the blocker here.
- Do not commit generated dashboards into this document by hand; use `docs/issue_dashboard.md`, `docs/issue_dashboard.json`, or Actions artefacts only when a future issue explicitly asks for generated snapshots.

## Assistant selection rule

When asked to take the next issue, an assistant should use this order:

1. inspect open issues;
2. prefer `agent-ready` issues;
3. avoid `status:blocked`, `needs-human`, and `needs-acceptance-criteria`;
4. prefer `priority:P0`, then `priority:P1`, then `priority:P2`;
5. prefer `size:small` before larger work;
6. implement one issue only through the patch-submission broker.
