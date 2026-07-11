# End-of-Project Retrospective

Date: 2026-07-11

## Executive assessment

The project did a good job overall. It turned an initially underspecified Paper2Code validation problem into a working, auditable repository with three concrete outputs:

- static validation of paper claims;
- public-data market reconstruction and metric calculation;
- a functional AGENTICAITA architecture replication with deterministic and LLM-backed agent paths.

The strongest outcome is methodological honesty. The repository does not overclaim empirical reproduction. It documents that the original paper's live Hyperliquid candles, L2 snapshots, LLM decisions, SQLite logs, and execution context are not available through the public artefacts we have. The final position is therefore precise: the code supports functional architecture replication and plausibility testing, but it cannot independently prove the paper's original live-session results.

The second strongest outcome is operational maturity. Across 72 pull requests, 70 were merged, 2 were closed unmerged, and none remained open at the time of this update. The repository now has issue-native workflow support, patch-envelope submission automation, run manifests, result dashboards, GitHub Actions smoke checks, documentation link validation, Wiki sync, release-oriented snapshot workflows, compact evidence bundles, and a clear agent guidance profile.

The main weakness is that the project accumulated process and reporting infrastructure faster than it converged on a small number of final scientific claims. Late work exposed several correctness gaps: agentic friction double-counting, Risk Manager rejection accounting, symbol de-duplication in the 76-symbol universe, missing compact reproducibility bundles, broken documentation links after reorganization, LLM output-contract opacity, and a BTC benchmark contradiction for the paper window. Follow-up PRs #136 through #141 addressed those repository-level gaps. The remaining limitation is now primarily scientific rather than operational: the original AGENTICAITA artefacts needed for empirical reproduction are still unavailable.

Overall grade: **A-**.

The codebase is useful, tested, and transparent. The research result is appropriately cautious. The late correctness and reproducibility issues were closed, but the paper's original dry-run remains independently unverifiable without primary artefacts from the authors.

## Evidence reviewed

This retrospective reviewed repository state and GitHub metadata at the end of the project:

- 72 pull requests total;
- 70 merged pull requests;
- 2 closed-but-unmerged pull requests: #60 and #51;
- 0 open pull requests at review time;
- 70 issues total;
- 70 closed issues;
- 0 open issues;
- 324 commits since 2026-05-16 across all refs;
- 11,828 tracked Python lines across repository scripts, validation, replication, and tests;
- 3,233 tracked Markdown documentation lines under `docs/`;
- 905 workflow YAML lines across 10 GitHub Actions workflows;
- 132 pytest tests passing locally across the three independent suites.

Local test results observed during this retrospective:

| Suite | Result |
| --- | ---: |
| Root `tests/` | 62 passed |
| `validation` tests | 7 passed |
| `replication` tests | 63 passed |

## What we built

### Validation module

The `validation/` module started the project on a strong footing by separating paper-claim auditing from replication. It checks static claims, reports unsupported claims, and can optionally use real market data when a local database is available.

This was a good design choice. It avoided conflating three different questions:

- Are the paper's reported numbers internally consistent?
- Can public data approximate the stated market window?
- Can an executable architecture produce similar aggregate behaviour?

The validation path remained small and stable. It has focused tests and a clear CLI. That stability is a sign that the project carved the problem boundary correctly.

### Market-data tooling

The project added standalone scripts for fetching Hyperliquid OHLCV and funding data, storing data in SQLite, reporting coverage, exporting replication inputs, and computing AZTE/CBD metrics.

The strongest result here is the documented negative finding: the paper-window Hyperliquid one-minute candles are not recoverable from the current documented public candle endpoint because the endpoint only retains the most recent 5,000 candles. The investigation correctly distinguishes this from a general Hyperliquid failure, since funding data was returned for the same requested symbols and window.

This matters because it prevents false confidence. The project did not silently switch venues and pretend equivalence. It labelled Binance USD-M or Bybit as fallback venues and preserved the limitation in reports.

### Replication module

The `replication/` module became the repository's main technical artifact. It implements:

- AZTE event triggering;
- CBD correlation-break scoring;
- Sequential Analyst, Risk Manager, and Executor pipeline;
- deterministic proxy agents;
- LLM-backed Analyst and Risk Manager agents through OpenRouter;
- risk gates, cooldowns, and OHLCV intrabar stop-loss/take-profit execution;
- synthetic and real-data CLI runs;
- sweep support;
- audit logs, summaries, reports, evidence bundles, and comparison tools.

The architecture is clear enough to run, inspect, and test. The largest core replication files are still moderate in size: `agents_llm.py` at 365 lines, `simulator.py` at 261 lines, `replicate.py` at 256 lines, and `llm.py` at 200 lines. That is a healthy size for this project stage.

The calibrated real-data report shows the project reached a meaningful functional approximation:

| Metric | Initial real-data run | Calibrated real-data run | Paper reported |
| --- | ---: | ---: | ---: |
| Total invocations | 277 | 169 | 157 |
| Trades executed | 265 | 153 | 139 |
| Agentic friction | 6.86% | 12.43% | 11.46% |
| Win rate | 43.02% | 47.71% | 51.80% |
| Profit factor | 0.672 | 0.841 | 0.841 |
| Net PnL | -$37.32 | -$9.34 | -$15.07 |

Those figures are not proof of reproduction, but they are a credible demonstration that the published architecture can be represented in executable form and tuned into a paper-like aggregate regime.

### LLM-backed path

The LLM work was ambitious and valuable. The project added:

- a pluggable LLM provider abstraction;
- OpenRouter integration;
- field-level response validation;
- retry handling;
- CLI configuration overrides;
- sweep support for LLM agents;
- a live smoke path;
- audit logging;
- deterministic-vs-LLM comparison reports.

The final LLM-backed run completed end-to-end using `qwen/qwen-2.5-7b-instruct` through OpenRouter. It was correctly labelled as a behavioural comparison rather than a reproduction of the paper's exact `qwen3.5:9b` remote Ollama path.

The comparison surfaced a major behavioural difference:

| Metric | Deterministic baseline | LLM-backed candidate | Delta |
| --- | ---: | ---: | ---: |
| Total invocations | 173 | 173 | 0 |
| Trades executed | 139 | 11 | -128 |
| Risk approved | 139 | 11 | -128 |
| Risk rejected | 34 | 162 | +128 |
| Win rate | 34.53% | 18.18% | -16.35 pp |
| Profit factor | 0.566 | 0.108 | -0.458 |
| Net PnL | -$34.73 | -$7.98 | +$26.74 |

This was useful, but the first run was not fully resolved. Issue #135 correctly captured that interpretation was confounded by output-contract failures and opaque gate outcomes. The LLM path was real, but final conclusions from that run needed better output contracts, rejection diagnostics, and comparison reporting.

The follow-up in PR #141 improved this materially. The LLM path now distinguishes valid model behaviour from bounded repair, deterministic fallback, hard-gate rejection, and Analyst abstention in pipeline logs and summaries. That does not rescue the original OpenRouter run as a clean behavioural measurement, because it lacked the new provenance fields, but it gives future LLM runs the diagnostics needed for defensible interpretation.

### Documentation and reports

Documentation became one of the project's strengths. The repository now contains reports, investigations, runbooks, Wiki source pages, CI-operation notes, issue-tracking docs, and replication workflow documentation.

The best documentation choices were:

- separating investigations from final reports;
- documenting failed or impossible paths, especially Hyperliquid paper-window recovery;
- recording commands used for large runs;
- making local/generated artifact paths explicit without committing large data;
- keeping the conclusion cautious about empirical reproduction.

The weakest documentation moment came late, when PR #129 reorganized docs into topical subfolders but left broken cross-references. PR #136 repaired those links and added Markdown link validation, so the reorganization is now on a safer footing.

### Process automation

The project invested heavily in automation:

- issue label setup;
- structured issue forms;
- issue dashboard generation;
- issue hygiene checks;
- Wiki sync;
- results-surface smoke checks;
- run manifest generation;
- dashboard rendering;
- artifact upload;
- paper-window snapshot workflows;
- single-file patch-submission envelope broker;
- local envelope validator;
- Markdown link validation;
- compact reproducibility evidence generation.

This was more process than a small research repository strictly needs, but it paid off by making agent-driven work safer and more repeatable. The envelope broker and local validator were especially important once the repository started using a controlled patch-submission workflow.

The downside is complexity. There are 10 workflows and 905 lines of workflow YAML. Several workflow-related PRs were needed to fix startup failures, input types, and minimal definitions. That pattern suggests the automation was valuable but introduced its own maintenance burden.

## PR-by-PR trajectory

The PR history shows six phases.

### Phase 1: Data and static validation, PRs #8-#17

Early work established the market-data and validation foundations:

- #8 added Hyperliquid OHLCV download support;
- #9 added storage and coverage reporting;
- #10 qualified funding history;
- #11 computed AZTE and CBD metrics;
- #12 integrated real-data validation mode;
- #13 and #14 documented historical reconstruction limits and validation plans;
- #15 added issue-to-PR automation;
- #16 and #17 added the Paper2Code reference and scope clarifications.

This phase was strong. It identified data availability as the core constraint and avoided premature claims.

### Phase 2: Replication harness and real-data approximation, PRs #34-#50

This phase moved from validation into executable replication:

- #34 documented a real-data baseline;
- #35 preserved full OHLCV inputs;
- #36 added OHLCV stop-loss and take-profit execution;
- #37 added run metadata;
- #38 added calibration sweep support;
- #39 added large-universe workflow support;
- #45 added funding-aware reporting;
- #47 documented Hyperliquid OHLCV availability limitations;
- #48 defined artifact retention policy;
- #49 added a reproducible real-data command script;
- #50 added replication output quality checks.

This was the core scientific build-out. The quality improved because each PR narrowed a specific replication fidelity gap.

### Phase 3: Results surfaces, Wiki, and issue-native workflow, PRs #52-#85

This phase made the repository easier to operate:

- #52 staged Wiki methodology pages;
- #57, #58, #59, and #61 added manifests, result indexing, dashboards, summaries, and artifacts;
- #64 and #65 added paper-window snapshot workflows;
- #67 and #69 added Wiki sync and smoke testing;
- #71 clarified Wiki seeding;
- #73, #75, #77, #81, #82, #83, and #85 built the issue-native planning system.

The project became much more maintainable. The tradeoff is that some infrastructure work displaced time that could have been spent tightening final scientific accounting.

### Phase 4: Workflow stabilization and patch broker, PRs #89-#116

This phase was about making agentic contribution safer:

- #89 and #90 added issue hygiene and dashboard artifact workflows;
- #95, #97, #99, and #101 fixed and simplified manual report workflows;
- #104 added the OpenRouter provider abstraction;
- #105 wired LLM-backed agents;
- #111 refactored LLM agents and retry handling;
- #113, #114, and #115 added LLM CLI, sweep, and smoke support;
- #116 added the local patch-submission envelope validator.

The project matured operationally here. The repeated failures and retries around some patch envelopes and workflows were not ideal, but the final state is much safer than the initial one.

### Phase 5: Final reports and investigations, PRs #118-#129

The final phase synthesized results:

- #118 added a paper replication gap report;
- #124 computed BTC benchmark alpha in replication reports;
- #125 documented Hyperliquid paper-window OHLCV constraints;
- #126 documented deterministic signal-mix divergence;
- #127 reported the 76-symbol fallback replication;
- #128 reported the LLM-backed replication comparison;
- #129 reorganized docs into topical subfolders.

This phase was productive and honest, but it also surfaced the final unresolved issues that became the closure backlog for the next phase.

### Phase 6: Closure fixes and recovered reports, PRs #136-#142

The post-retrospective phase closed the remaining repository-level gaps:

- #136 repaired documentation links and added Markdown link validation;
- #137 corrected pipeline-stage accounting and agentic-friction calculations;
- #138 selected large-universe contracts by unique normalized base asset and documented the remaining local-data rerun boundary;
- #139 investigated the BTC benchmark-window contradiction and preserved it as a material paper-evidence issue;
- #140 added compact reproducibility evidence bundles under `docs/evidence/`;
- #141 improved LLM contracts, bounded repair, provenance, and diagnostic reporting;
- #142 recovered additional AGENTICAITA reports.

This phase changed the retrospective's final assessment. The project is no longer best described as near-complete with six open repository issues. It is better described as technically closed for the present scope, with the unresolved boundary shifted to missing author artefacts and any future fresh live LLM rerun using the improved diagnostics.

## What went well

### The project avoided false reproduction claims

This is the most important success. It would have been easy to tune outputs until they matched the paper and present that as reproduction. Instead, the project repeatedly distinguished:

- functional architecture replication;
- public-data fallback replication;
- calibrated aggregate approximation;
- empirical reproduction of the original live dry-run.

Only the first three are supported. The fourth is not, because the required original artifacts are absent.

### Negative findings were preserved

The Hyperliquid paper-window investigation is a high-quality negative result. It records the attempted command, observed zero-candle result, funding-data contrast, official 5,000-candle retention constraint, historical archive limitations, and the decision to use a labelled fallback venue.

This is exactly what a replication project should do when data cannot be recovered.

### The architecture is executable and inspectable

The project now has real CLIs, tests, reports, and audit outputs. It is not just prose. A user can run static validation, synthetic replication, real-data replication when local data exists, LLM smoke checks, comparison scripts, quality checks, and result dashboards.

### The deterministic proxy was treated carefully

The deterministic signal-mix investigation made the right decision: do not hard-code the paper's long bias into a transparent deterministic proxy without a paper-grounded mechanism. The paper's 142 long, 2 short, and 13 wait signal mix is an empirical property of one LLM prompt/model/context/session, not a deterministic rule.

### Tests are broad enough for the repository's shape

The three pytest suites passed locally:

- 62 root script tests;
- 7 validation tests;
- 63 replication tests.

For a research/reproducibility repository without a package boundary, this is a good level of coverage. The tests cover scripts, validation, replication, LLM support, live-smoke fallback behaviour, manifests, dashboards, and comparison tooling.

### The repo became agent-friendly

The issue-to-PR workflow, patch-submission envelope, local validator, repo profile, and AGENTS instructions make future AI-assisted work safer. The project learned from earlier process failures and encoded those lessons into tooling.

## What did not go well

### Final accounting needed late correction

Issue #130 reported that agentic friction double-counted Analyst waits and that Risk Manager rejection accounting was not quite right. This was not cosmetic. Agentic friction is one of the paper-facing headline metrics, so PR #137 correctly fixed the accounting before final claims were frozen.

### The initial 76-symbol run was not actually 76 unique base assets

The fallback report stated that 76 selected source symbols normalized to 69 distinct assets. PR #138 corrected the exporter to select by unique normalized base asset before applying the requested limit and documented the local-data boundary for reruns. The committed historical report remains useful, but its title and interpretation require that distinction.

### Reproducibility evidence arrived late

The repository intentionally avoids committing large market databases, raw LLM audit logs, and full result directories. That is correct. Issue #132 pointed out the consequence: committed reports were harder to independently verify without compact evidence bundles.

PR #140 added that middle layer through small JSON evidence bundles under `docs/evidence/`, preserving checksums, selected summary extracts, coverage samples, and command provenance without committing large generated artifacts.

### Documentation links broke during reorganization

PR #129 improved the docs structure, but only one cross-reference was initially updated. PR #136 repaired the links and added validation. Link checking should have accompanied the reorganization from the start.

### LLM output contracts were too opaque in the first run

The LLM-backed run completed, but issue #135 noted output-contract failures and opaque gate outcomes. PR #141 added signal-aware contracts, bounded repair, decision provenance, and summary diagnostics. The original run still should not be overinterpreted, but future runs can now distinguish model decisions, schema failures, fallback decisions, retry exhaustion, and Risk Manager gate reasons.

### Automation took several attempts to stabilize

The workflow and patch-envelope history includes failed attempts and v2/v3/v4/v5 submissions. This is normal in a fast agentic project, but it shows that the process layer was complex enough to become a project in itself.

## Residual risk register

The six repository issues that were open during the first retrospective pass are now closed. The residual risks are narrower and mostly external to the repository.

| Area | Status | Residual risk | Severity |
| --- | --- | --- | --- |
| Original author artefacts | Not available | Exact empirical reproduction remains impossible without original SQLite logs, prompts, completions, L2 snapshots, funding records, and execution context. | High |
| Fresh LLM diagnostic rerun | Tooling ready, not committed | The original LLM run lacks the new provenance fields; a future workstation run with retained market input and `OPENROUTER_API_KEY` is needed for clean behavioural claims. | Medium/High |
| Unique-base-asset large-universe rerun | Exporter fixed | The corrected selection policy is implemented, but a full corrected rerun still depends on a local market database that is intentionally not committed. | Medium |
| BTC benchmark contradiction | Investigated and documented | The contradiction remains a paper-evidence problem until the authors provide exact benchmark construction and funding treatment. | Medium/High |

## Quality of engineering

### Strengths

The engineering quality is good for a research validation repository:

- small, focused Python modules;
- clear command-line entry points;
- no unnecessary packaging layer for the root scripts;
- separate `validation/` and `replication/` concerns;
- local tests for scripts and replication internals;
- generated artifacts excluded from git;
- reports include commands and caveats;
- CI smoke checks exercise validation and synthetic replication;
- LLM integrations have deterministic fallback and live-smoke paths.

The codebase is pragmatic rather than over-engineered. Most modules are under a few hundred lines, and the repository avoids pretending to be a polished installable package.

### Weaknesses

The main engineering weaknesses are structural and operational:

- three disjoint pytest suites require humans and agents to remember separate commands;
- no unified lint/typecheck configuration exists;
- CI now runs selected pytest coverage through results-surface and specialized workflows, but there is still no single unified test command enforced everywhere;
- root `scripts/` is not a package, so imports rely on path adjacency and `sys.path` insertion in places;
- workflow count and YAML complexity are high for the repository size;
- final reports depend on local generated artifacts that are intentionally not committed;
- compact evidence bundles reduce, but do not eliminate, dependence on local generated artifacts.

None of these invalidate the project. They are normal tradeoffs for a fast-moving, issue-driven research repo. But if the repository were to become a long-lived public reference implementation, these would be the next maintainability targets.

## Quality of science

The science is strongest where it is falsifiable and cautious:

- Hyperliquid paper-window candles are not publicly recoverable through the documented current candle endpoint.
- The original L2 snapshots, LLM decisions, SQLite logs, and exact execution context are missing.
- A deterministic proxy can implement the architecture but cannot reproduce LLM narrative bias.
- A calibrated public-data run can approximate aggregate metrics but cannot prove original empirical claims.
- LLM-backed behaviour can be executed, and future runs now have better diagnostics, but the first large LLM run remains provisional because it predates the improved provenance fields.

The science is weakest where calibration risks becoming target matching. The project handled this mostly well by labelling calibrated and fallback runs explicitly. The remaining danger is that readers may overfocus on close aggregate numbers and underweight the missing original artifacts.

The final reports should keep the following sentence near the top of any public summary:

> This repository provides a functional, auditable approximation of the AGENTICAITA architecture on public or synthetic data; it does not reproduce the original live dry-run because the original market snapshots, LLM decisions, execution logs, and retained Hyperliquid paper-window candles are unavailable.

## How good a job did we do?

We did a good job because the repository now answers the original question more rigorously than a simple pass/fail reproduction attempt would have.

The answer is nuanced:

- The paper's architecture is implementable.
- The reported aggregate shape is plausible under calibrated public-data replication.
- The exact live empirical result is not independently reproducible from available public artifacts.
- Venue substitution, missing L2 data, missing model decisions, and retention-limited candles are material gaps.
- The LLM-backed path works technically, but final behavioural conclusions require a fresh run using the improved diagnostics.

That is a valuable outcome. It is not as satisfying as an exact reproduction, but it is much more honest.

The project now earns A-: strong execution, strong transparency, meaningful code, closed repository-level correctness gaps, and an appropriately cautious scientific conclusion. It does not earn a full A only because exact empirical reproduction remains impossible without primary artefacts from the original authors, and the improved LLM diagnostics still need a fresh live run before stronger behavioural claims are made.

## Final recommendations

Before calling the paper empirically reproducible, external artefacts are still required:

1. Original SQLite decision and execution logs.
2. Original prompts, completions, model/provider configuration, and retry/fallback records.
3. Original L2 order-book snapshots, funding records, and execution-time market state.
4. Exact BTC benchmark construction and funding treatment.
5. A fresh LLM run using the improved contract/provenance diagnostics if new behavioural claims are desired.

For a final release, include:

- the static validation report;
- the Hyperliquid availability investigation;
- the deterministic public-data replication report;
- the LLM-backed comparison report;
- compact evidence bundles and checksums;
- exact commands and dependency notes;
- a clear statement of non-reproducible original artifacts.

## Closing reflection

The project succeeded most where it behaved like an audit rather than a demo. It resisted overclaiming, documented data limits, built executable tools, tested them, and surfaced its own remaining weaknesses. That is the right posture for paper-to-code validation.

The final lesson is that reproducibility depends as much on artifact retention as on code. A paper can describe an architecture well enough to reimplement it, but without retained market snapshots, prompts, model outputs, and execution logs, exact empirical reproduction remains out of reach. This repository makes that boundary visible.
