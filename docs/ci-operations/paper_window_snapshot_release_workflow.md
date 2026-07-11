# Paper-Window Snapshot Release Workflow

This repository keeps raw market data and full generated run outputs out of git. Retained real-data snapshots should be stored as GitHub Release assets, with only a compact pointer manifest and curated documentation committed to the repository.

## Recommended flow

1. Run the manual paper-window real-data workflow and inspect its temporary Actions artefact.
2. Promote the selected successful Actions artefact with `Promote Paper Window Snapshot`.
3. Future workflows use `Verify Paper Window Snapshot` or the same download commands to retrieve and verify the retained snapshot.

## Release asset shape

Recommended release tag:

```text
paper-window-real-data-20260406-20260411
```

Recommended assets:

```text
paper-window-real-data-20260406-20260411.tar.gz
paper-window-real-data-20260406-20260411.tar.gz.sha256
paper-window-real-data-20260406-20260411.manifest.json
```

The archive contains coverage reports, complete-symbol lists, run manifests, replication summaries, quality reports, result indexes, dashboard output, diagnostic logs, and optionally the exported `replication_input_ohlcv.csv`.

The archive does not include raw SQLite databases, raw per-symbol OHLCV directories, broker archives, caches, bytecode, or local machine files.

## Promotion workflow

Run `Promote Paper Window Snapshot` manually with:

- the workflow run id that produced the temporary paper-window artefact;
- optionally the exact artefact name;
- the release tag;
- whether to include `replication_input_ohlcv.csv`;
- whether to overwrite release assets.

The workflow downloads the selected Actions artefact, packages the retained subset, writes a checksum, writes a release manifest, uploads release assets, and uploads a pointer manifest as a workflow artefact.

## Consumer workflow

Run `Verify Paper Window Snapshot` to confirm the release asset can be downloaded, checksum-verified, and extracted by GitHub Actions.

Equivalent shell commands:

```bash
gh release download paper-window-real-data-20260406-20260411 \
  --pattern 'paper-window-real-data-20260406-20260411.tar.gz' \
  --pattern 'paper-window-real-data-20260406-20260411.tar.gz.sha256' \
  --pattern 'paper-window-real-data-20260406-20260411.manifest.json'

sha256sum -c paper-window-real-data-20260406-20260411.tar.gz.sha256
tar -xzf paper-window-real-data-20260406-20260411.tar.gz
```

## Interpretation limits

This retained snapshot is a public-market comparable reconstruction. It does not recover the original order book snapshots, prompts, LLM calls, agent deliberations, risk-manager approvals, dry-run SQLite records, or execution assumptions.
