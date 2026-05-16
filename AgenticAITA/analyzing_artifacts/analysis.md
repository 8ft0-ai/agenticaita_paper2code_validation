# Analysis artefact

The validation targets the claims that can be checked without access to raw trading records:

- Agentic friction: `(N_rej + N_wait) / N`.
- Pipeline table percentages: long, short, wait, approved, rejected, trades executed.
- PnL and benchmark table arithmetic.
- Core performance metrics: net PnL, profit factor, mean win/loss, risk/reward, break-even win rate, asset breadth.
- Binomial significance: exact one-sided and two-sided tests, plus the normal approximation implied by the paper's `p ≈ 0.34` statement.
- Transaction-cost sensitivity table.
- AZTE false-positive rate statement: one-sided `Z >= 2` versus two-sided `|Z| >= 2`.
- CBD formula properties: boundedness of the saturated anomaly term and monotonicity in decorrelation for identical anomaly magnitude.

Claims requiring unavailable data are explicitly marked as `unsupported`: raw SQLite provenance, funding-corrected BTC benchmark, live zero-intervention execution, qwen/Ollama telemetry, per-asset CBD correlations, and no-post-processing figure claims.
