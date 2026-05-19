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

## First-run Wiki seeding

GitHub may not create the backing `.wiki.git` repository until the Wiki has been saved once through the GitHub web UI. In that state, the workflow can have a valid `WIKI_PUSH_TOKEN` and still fail with a repository-not-found error when cloning the Wiki remote.

Before the first workflow run, open the repository Wiki in the browser, create a minimal `Home` page, and save it. After that one-time seed, rerun the workflow; it should be able to clone the Wiki remote and replace the seed page with the reviewed files from `docs/wiki/`.

## Publication behaviour

The workflow validates that `docs/wiki/Home.md` exists, then publishes all Markdown files in `docs/wiki/` to the Wiki repository root. It removes existing root-level Wiki Markdown pages before copying the staged pages, so `docs/wiki/` remains the source of truth.

The workflow commits to the existing current branch of the Wiki repository. If cloning the Wiki remote fails, it exits with an error that points maintainers to the one-time Wiki UI seed step.

## Failure modes

The workflow exits with a clear error when:

- `docs/wiki/` is missing;
- `docs/wiki/Home.md` is missing;
- there are no staged Markdown pages;
- `WIKI_PUSH_TOKEN` is not configured;
- the Wiki remote cannot be cloned, which usually means the Wiki has not yet been seeded once through the GitHub UI;
- the Wiki remote can be cloned but cannot be pushed.

No generated Wiki build outputs are committed to `main`.
