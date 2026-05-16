# AGENTICAITA replication harness

This repository moves the previous PDF-only claim audit one step closer to replication.

It implements an executable dry-run version of the published architecture:

1. **AZTE**: rolling absolute-return z-score trigger plus absolute-return floor.
2. **CBD**: saturated anomaly score plus correlation-break diversification score.
3. **SDP**: sequential Analyst -> Risk Manager -> Executor pipeline using typed contracts.
4. **Risk hard gates**: directional signal, confidence >= 0.60, stop distance <= 2%, size <= US$500.
5. **IGP**: global and per-asset cooldowns to approximate serialised inference admission.
6. **Audit artefacts**: `pipeline_log`, `trades`, and `vol_history` written to CSV and SQLite.
7. **Cost sensitivity**: paper-style round-trip notional cost scenarios.

## Important boundary

This is a **functional architecture replication**, not an empirical replication of the authors' five-day live dry-run.
It does not prove the reported 157 invocations, 139 trades, zero intervention, BTC benchmark, or CBD asset outcomes.
Those require the author's raw SQLite database, market snapshots, order books, funding rates, prompts, LLM outputs,
and exact exchange/session configuration.

## Run

```bash
pip install -r requirements.txt
python replicate.py --config config.yaml --out results
pytest -q
```

Optional real-data input:

```bash
python replicate.py --input-csv path/to/ohlcv.csv --out results_real_data
```

The CSV must contain at least: `timestamp,asset,close`.

## Outputs

- `results/agenticaita_replication.sqlite`
- `results/pipeline_log.csv`
- `results/trades.csv`
- `results/vol_history.csv`
- `results/summary.json`
- `results/replication_report.md`

## What this adds beyond the earlier claim audit

The earlier audit checked whether reported numbers were internally consistent. This harness checks whether the described
architecture can be made executable and auditable under the published equations and gates. It also creates the same class
of artefacts that would be needed to compare against the paper's claims.
