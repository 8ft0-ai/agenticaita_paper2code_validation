# Paper2Code-style planning artefact: AGENTICAITA claim validation

## Objective
Build a minimal, reproducible Python validation repository that checks numeric, statistical, and formula-level claims in *AGENTICAITA: A Proof-of-Concept About Deliberative Multi-Agent Reasoning for Autonomous Trading Systems*.

## Scope
The paper does not provide the underlying SQLite database (`trades`, `vol_history`, `pipeline_log`, `ollama_calls`) or market data. The validation therefore separates:

1. **Recomputable claims**: arithmetic derived from reported tables and formulas.
2. **Statistical claims**: binomial p-values and normal-tail false-positive rates.
3. **Formula/property claims**: CBD monotonicity and boundedness.
4. **Unsupported empirical claims**: claims requiring raw logs, fills, funding rates, market data, or the production database.

## Implementation plan
- Encode reported quantities in `claims.py`.
- Implement validation functions in `metrics.py` using only transparent mathematical operations.
- Implement an executable runner in `validate_claims.py` that emits Markdown, JSON, and CSV outputs.
- Add tests in `tests/test_claims.py` to make the validation reproducible.
- Produce a final `validation_report.md` that records which claims passed, which are qualified, and which cannot be verified from the paper alone.
