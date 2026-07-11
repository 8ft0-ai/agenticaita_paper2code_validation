# Issue Dashboard Runbook

The issue dashboard is a generated, factual snapshot of GitHub issue metadata. It complements the curated roadmap in `docs/roadmap.md`; it does not replace the roadmap, labels, milestones, or issue comments.

Use the dashboard when you need a board-like view that is visible to humans, GitHub Actions, and assistant-driven development sessions without relying on GitHub Projects.

## Source of truth

The source of truth remains:

- GitHub issues;
- issue labels;
- milestones;
- issue comments;
- pull requests;
- checked-in roadmap and design documentation.

The dashboard reports what that metadata says at generation time. Update issue metadata first, then regenerate the dashboard.

## Prerequisites

Install and authenticate the GitHub CLI:

```bash
gh auth login
gh auth status
```

The authenticated account or token must be able to read issues in this repository.

## Generate a Markdown dashboard

Print the Markdown dashboard to stdout:

```bash
python scripts/generate_issue_dashboard.py \
  --repo 8ft0-ai/agenticaita_paper2code_validation
```

Write the Markdown dashboard to a local file:

```bash
python scripts/generate_issue_dashboard.py \
  --repo 8ft0-ai/agenticaita_paper2code_validation \
  --markdown-output docs/issue_dashboard.md
```

## Generate Markdown and JSON snapshots

```bash
python scripts/generate_issue_dashboard.py \
  --repo 8ft0-ai/agenticaita_paper2code_validation \
  --markdown-output docs/issue_dashboard.md \
  --json-output docs/issue_dashboard.json
```

Use a deterministic timestamp for tests or comparisons:

```bash
python scripts/generate_issue_dashboard.py \
  --repo 8ft0-ai/agenticaita_paper2code_validation \
  --generated-at-utc 2026-01-01T00:00:00Z \
  --markdown-output /tmp/issue_dashboard.md \
  --json-output /tmp/issue_dashboard.json
```

## State filters

The default state filter is `open`.

```bash
python scripts/generate_issue_dashboard.py --repo 8ft0-ai/agenticaita_paper2code_validation --state open
python scripts/generate_issue_dashboard.py --repo 8ft0-ai/agenticaita_paper2code_validation --state closed
python scripts/generate_issue_dashboard.py --repo 8ft0-ai/agenticaita_paper2code_validation --state all
```

Use `--limit` to control how many issues are fetched from GitHub.

## Output policy

Generated dashboard files are operational snapshots. They may be useful locally or in Actions artefacts.

Do not commit generated dashboard output by default. Commit `docs/issue_dashboard.md` or `docs/issue_dashboard.json` only when a future issue explicitly asks for a reviewed snapshot or a deterministic fixture.

Never overwrite `docs/roadmap.md` with generated dashboard content. The roadmap is curated and explains sequencing; the dashboard is generated and reports current metadata.

## Interpretation

The dashboard groups issues by:

- `agent-ready`;
- blocked state;
- `status:*`;
- `priority:*`;
- `area:*`;
- milestone;
- metadata completeness.

Metadata warnings are advisory. They indicate that an issue may be missing labels or may have contradictory labels, such as `agent-ready` combined with `status:blocked`.

## Relationship to other docs

- `docs/issue_management.md` defines the issue-native operating model and label taxonomy.
- `docs/issue_dashboard_design.md` defines the dashboard schema and grouping rules.
- `docs/roadmap.md` remains the curated planning index.

