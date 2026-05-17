# Single-file patch submission

Use this prompt when taking one issue to a broker-generated PR.

```text
Take <issue-url> in 8ft0-ai/agenticaita_paper2code_validation to a reviewable PR using the single-file patch-submission envelope broker.

Rules:
- Read the issue first.
- Keep the change scoped to the issue.
- Prepare a unified patch against main.
- Submit exactly one envelope file to .patches/inbox/<submission-id>.patch-submission on the existing patch-submissions branch.
- Do not create an implementation branch manually.
- Do not create a pull request manually.

Repository validation:
- Use pip install -r requirements.txt when dependencies are needed.
- For downloader changes, consider python scripts/fetch_hyperliquid_ohlcv.py --symbol-limit 3.
- For AZTE/CBD metric changes, consider python scripts/compute_azte_cbd_metrics.py --symbols BTC/USDC:USDC,ETH/USDC:USDC.
- For validation logic, consider cd validation && python validate_claims.py --out results.
- Do not include generated market data, SQLite DBs, validation results, replication outputs, coverage reports, caches, bytecode, or broker archives.

After submission, check the generated PR and the processed or failed archive.
Report the PR link, changed files, validation performed, skipped checks, and limitations.
```
