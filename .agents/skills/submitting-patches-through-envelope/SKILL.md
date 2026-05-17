---
name: submitting-patches-through-envelope
description: Use this skill when submitting an existing implementation patch through the single-file `.patch-submission` envelope broker.
---

# Submitting Patches Through Envelope

## When to use this skill

Use this skill when the user asks to submit a patch through the preferred envelope broker workflow.

## Hard rules

- Do not create a pull request manually.
- Do not apply the patch and commit materialised source changes.
- Push exactly one commit to the existing `patch-submissions` branch.
- That commit must contain exactly one file: `.patches/inbox/<submission-id>.patch-submission`.
- Do not submit a new envelope while another submission is unresolved.
- Never resubmit a failed envelope unchanged; regenerate from current `origin/main` and use a new `-v2` or split submission id.

## Procedure

1. Sync to latest `origin/main`.
2. Validate the implementation patch with `git apply --check`.
3. Run relevant tests or document why they were skipped.
4. Build one schema version 2 `.patch-submission` envelope.
5. Commit that one envelope to `patch-submissions` under `.patches/inbox/`.
6. Stop unless asked to inspect the generated PR or archive.

## Final response requirements

Always report:

```text
ISSUE_NUMBER
SUBMISSION_ID
BASE_COMMIT
IMPLEMENTATION_BRANCH
ENVELOPE_PATH
git apply --check result
tests/checks run
submitted commit hash
skipped validations
unresolved issues
post-submit status when checked
```
