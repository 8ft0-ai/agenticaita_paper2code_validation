# Wiki Sync Workflow

The staged GitHub Wiki source pages live in `docs/wiki/` so they can be reviewed through the normal repository pull-request process before publication.

The `Sync staged Wiki pages` GitHub Actions workflow publishes those reviewed pages to the repository Wiki.

## Trigger behaviour

The workflow runs when either of these events occurs:

- a maintainer manually starts `workflow_dispatch`;
- a push to `main` changes files under `docs/wiki/**`.

## Required secret

Configure a repository secret named `WIKI_PUSH_TOKEN` before running the workflow. The token must have permission to push to the repository Wiki remote:

```text
https://github.com/8ft0-ai/agenticaita_paper2code_validation.wiki.git
```

The default `GITHUB_TOKEN` is not used for the push because the Wiki is backed by a separate `.wiki.git` repository and may require explicit write credentials.

## Publication behaviour

The workflow validates that `docs/wiki/Home.md` exists, then publishes all Markdown files in `docs/wiki/` to the Wiki repository root. It removes existing root-level Wiki Markdown pages before copying the staged pages, so `docs/wiki/` remains the source of truth.

If the Wiki repository can be cloned, the workflow commits to its existing current branch. If cloning fails, the workflow attempts first-run initialisation by creating a local Wiki repository on `master` and pushing it to the `.wiki.git` remote.

## Failure modes

The workflow exits with a clear error when:

- `docs/wiki/` is missing;
- `docs/wiki/Home.md` is missing;
- there are no staged Markdown pages;
- `WIKI_PUSH_TOKEN` is not configured;
- the Wiki remote cannot be cloned, initialised, or pushed.

No generated Wiki build outputs are committed to `main`.
