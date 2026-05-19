# AGENTICAITA Replication Wiki

This page is the staged Home page for the repository Wiki. It is derived from committed repository documentation and should be copied to the enabled GitHub Wiki once the wiki git repository is available.

## Pages

- [Replication Methodology](Replication-Methodology)
- [Real-Data Replication Runbook](Real-Data-Replication-Runbook)
- [Evidence Ledger](Evidence-Ledger)
- [Artifact Requirements](Artifact-Requirements)

## Repository links

- Repository: https://github.com/8ft0-ai/agenticaita_paper2code_validation
- README: https://github.com/8ft0-ai/agenticaita_paper2code_validation/blob/main/README.md
- Artifact retention policy: https://github.com/8ft0-ai/agenticaita_paper2code_validation/blob/main/docs/artifact_retention_policy.md
- Real-data workflow runbook: https://github.com/8ft0-ai/agenticaita_paper2code_validation/blob/main/docs/real_data_replication_workflow.md
- Replication quality checks: https://github.com/8ft0-ai/agenticaita_paper2code_validation/blob/main/docs/replication_quality_checks.md
- Wiki tracking issue: https://github.com/8ft0-ai/agenticaita_paper2code_validation/issues/33

## Scope

The project contains two complementary validation paths. `validation/` checks whether reported paper quantities are internally consistent and flags unsupported claims. `replication/` runs a functional dry-run approximation of the published architecture and produces comparable artefacts from supplied market data.

Public APIs can reconstruct some market-condition inputs, but they cannot recover the original order book snapshots, prompts, LLM calls, risk-manager approvals, SQLite dry-run logs, or exact trade path without author artefacts.
