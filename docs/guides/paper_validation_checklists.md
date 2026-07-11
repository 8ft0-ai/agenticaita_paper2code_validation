# Paper Validation Checklists

Date: 2026-07-11

Use with [the operational guide](README.md). Record gate decisions rather than treating this as an informal to-do list.

## Intake and Gate A

- Freeze title, arXiv ID, paper version, URL, authors, and access date.
- Extract headline claims from abstract, introduction, principal tables, and conclusion.
- Assign claim importance and validation priority.
- Record extraction method, confidence, and manual verification for material values.
- Inventory released and missing artefacts with claim dependencies.
- Choose direct reproduction, independent replication, proxy replication, functional replication, synthetic replication, or diagnostic validation.
- State stopping rules and what further work could change the conclusion.
- Record Gate A decision.

## Artefact, legal, and data governance

- Original code, raw/processed data, splits, models, prompts, logs, checkpoints, and evaluation code are classified.
- Dataset licence and redistribution rights are recorded.
- API terms, scraping constraints, retention, and rate limits are recorded.
- Personal or sensitive data and jurisdictional constraints are assessed.
- Provider/model-output retention restrictions are assessed.
- External artefact owner, location, checksum, and expiry are defined.
- Every missing material artefact has an explicit reproduction consequence.

## Claim ledger and Gate C

- Every critical headline and benchmark claim has a stable ID.
- Dataset sizes, filters, exclusions, windows, and operational claims are represented.
- Denominators, missing-data policy, benchmark construction, and statistical assumptions are explicit.
- Evidence references and status rationale are recorded.
- Status is separate from extraction confidence.
- Gate C confirms that compared metrics are well defined.

## Static and statistical validation

- Recompute totals, percentages, rates, benchmark deltas, and derived metrics.
- Recompute statistical tests only when inputs and assumptions are sufficiently reported.
- Test implemented formulas and edge cases.
- Preserve ambiguous denominators as unsupported or unresolved rather than inferring silently.
- Record exact formulas, commands, and results.

## Data reconstruction and Gate B

- Smoke-test before bulk download.
- Verify exact period, entities, granularity, schema, gaps, duplicates, and per-entity failures.
- Record endpoint/dataset version, access date, request parameters, licence, and retention.
- Label material substitutions as proxy data.
- Stop historical recovery when documented limits prove the window unavailable.
- Record Gate B decision.

## Replication design and Gate D

- Map paper components to implementation components and claim IDs.
- Record fidelity as exact, inferred, proxy, synthetic, or unavailable.
- Build the smallest implementation that can affect a material conclusion.
- Keep deterministic and stochastic paths separate.
- Make assumptions, repairs, fallbacks, and calibration explicit.
- Do not tune solely to match the headline result.
- Record Gate D decision.

## Expensive runs and Gate E

- Tiny-run and contract tests pass.
- LLM/stochastic outputs have field-level validation and bounded repair/fallback behaviour.
- Cost, storage, runtime, credentials, and approval owner are recorded.
- Environment capture includes OS, architecture, runtime, dependency digest, container/hardware, timezone, seeds, and provider versions.
- Manifest, provenance, summary, report, and checksum outputs are ready.
- Stopping conditions are written.
- Record Gate E before the promoted run.

## Evidence and retention

- Large/raw data and secret-bearing logs remain local or externally retained by policy.
- Compact evidence records command, commit, environment, inputs, outputs, hashes, and limitations.
- Negative findings and unavailable paths are retained.
- Reports link claim IDs to evidence.
- Evidence drift can be detected from hashes or regeneration checks.

## Final report and Gate F

- Lead with the narrowest supported conclusion and material unsupported/contradicted claims.
- State frozen paper version and project classification.
- Separate static validation, proxy reconstruction, functional implementation, and empirical findings.
- State missing author artefacts and unresolved questions.
- A clean-context reviewer verifies extraction, formulas, denominators, statuses, evidence, and language.
- The reviewed commit and corrections are recorded.
- Gate F is approved before publication or merge of the final assessment.
