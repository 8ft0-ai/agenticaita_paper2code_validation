---
name: issue-to-pr
description: Use when asked to implement a GitHub issue end-to-end: inspect the issue, plan the work, modify the repository, verify changes, commit, push, and open a pull request linked to the issue.
---

# Issue to PR

Use this skill when the user asks you to take a GitHub issue and drive it end-to-end: understand the issue, plan the implementation, make the code changes, verify them, commit them, push a branch, and open a detailed pull request.

## Accepted Inputs

Accept any of these forms:

- A GitHub issue URL, such as `https://github.com/OWNER/REPO/issues/123`
- An issue number, such as `#123` or `123`
- A natural-language request that names an issue to implement

Default to the current repository unless the user provides another repo.

If the repository or issue is ambiguous, ask one short clarification question before making changes.

## Core Workflow

1. Establish issue context.
2. Inspect the relevant code and documentation.
3. Produce a concise implementation plan.
4. Create or switch to a dedicated branch.
5. Implement the smallest correct change.
6. Run targeted and broad verification.
7. Commit the work.
8. Push the branch.
9. Open a detailed pull request linked to the issue.

## GitHub Issue Intake

Use `gh` for GitHub operations.

Start by reading the issue:

```bash
gh issue view ISSUE --json number,title,body,labels,assignees,state,url,comments
```

If the issue is not clearly identified, list open issues:

```bash
gh issue list --state open --limit 50
```

Read the issue body and comments carefully. Extract:

* Problem statement
* Acceptance criteria
* Constraints and non-goals
* Suggested implementation details
* Testing expectations
* Documentation expectations

If acceptance criteria are missing, infer practical criteria from the issue and state them briefly before implementation.

## Repository Inspection

Before editing, inspect the repository using targeted searches.

Find:

* Relevant entry points
* Existing tests
* Related documentation
* CLI conventions
* Storage conventions
* Output format conventions
* Dependency management conventions

Prefer modifying existing modules over creating new abstractions.

Avoid speculative rewrites. Keep changes focused on the issue.

## Planning

Before major edits, create a short working plan.

The plan should include:

* Files likely to change
* Implementation steps
* Verification commands
* Risks or open questions

Do not over-plan. If the issue is clear, proceed after the plan.

## Branching

Check the worktree before editing:

```bash
git status --short
git branch --show-current
```

Use a dedicated branch name:

```text
issue-ISSUE_NUMBER-short-slug
```

Examples:

```text
issue-1-hyperliquid-history
issue-5-real-data-cli
```

If there are unrelated uncommitted changes:

* Do not revert them.
* Avoid touching unrelated files.
* If the unrelated changes conflict with the issue work, ask the user how to proceed.

## Implementation Standards

Follow these standards:

* Make the smallest complete change that satisfies the issue.
* Preserve existing behavior unless the issue requires a behavior change.
* Keep existing output formats stable unless acceptance criteria require changes.
* Add tests for new logic.
* Add documentation only when user-facing commands or behavior change.
* Handle partial failures explicitly when working with external data sources.
* Do not add backward compatibility unless there is a concrete need.
* Do not introduce secrets or credentials.
* Do not place large downloaded datasets in git.

For data-fetching issues:

* Make downloads resumable or safely repeatable where feasible.
* Record metadata about exchange, symbols, timeframe, start/end, and failures.
* Keep raw data and generated reports separate.
* Add `.gitignore` entries for generated databases, caches, and large artifacts when needed.

## Verification

Run the most relevant checks first, then broader checks if available.

Common commands:

```bash
python validate_claims.py --out results
pytest -q
python -m pytest -q
```

For CLI additions, run the new command with a small fixture, dry-run, or smoke-test mode.

For network-backed functionality:

* Prefer tests that mock or fixture exchange responses.
* Do not require live network access for the test suite unless explicitly requested.

Record verification results for the pull request body, including commands that failed and why.

## Commit

Only commit once implementation and verification are complete. This is appropriate because this skill is only invoked for issue-to-PR execution.

Before committing, inspect changes:

```bash
git status --short
git diff
```

Commit message format:

```text
<verb> <concise issue-focused summary>
```

Examples:

```text
add hyperliquid historical data downloader
integrate real-data validation cli
document historical reconstruction workflow
```

Never commit:

* Secrets
* `.env` files
* Credentials
* Downloaded market databases
* Large generated artifacts

## Pull Request

Push the branch and create the pull request with `gh`:

```bash
git push -u origin BRANCH

gh pr create --title "TITLE" --body "$(cat <<'EOF'
## Summary
- ...

## Issue
Closes #ISSUE_NUMBER

## Implementation
- ...

## Testing
- [x] `command`
- [ ] `command` not run: reason

## Risks and Limitations
- ...

## Generated Artifacts
- ...
EOF
)"
```

The pull request title should be action-oriented and specific.

The pull request body must include:

* Summary of the change
* Linked issue using `Closes #N`
* Implementation details
* Test and verification commands with outcomes
* Risks, limitations, or intentionally unsupported items
* Notes about generated files or artifacts excluded from git

For historical-data reconstruction work, explicitly mention that public APIs cannot recover original L2 order book snapshots, original LLM decisions, or the paper's original SQLite logs unless those artifacts are provided.

## Completion Response

After opening the pull request, respond with:

* Pull request URL
* Issue URL or number
* Verification summary
* Residual risks or follow-up work

Keep the final response concise.

## Safety Rules

Never:

* Force-push unless explicitly requested
* Use destructive git commands such as `git reset --hard` or `git checkout --` unless explicitly approved
* Amend commits unless explicitly requested
* Modify unrelated user changes
* Commit downloaded datasets or credentials

If an external API is unavailable, degrade gracefully and document the limitation.
