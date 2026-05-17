# AGENTICAITA replication

This directory moves the PDF-only claim audit in `../validation/` one step closer to executable replication.

It implements an executable dry-run version of the published architecture:

1. **AZTE**: rolling absolute-return z-score trigger plus absolute-return floor.
2. **CBD**: saturated anomaly score plus correlation-break diversification score.
3. **SDP**: sequential Analyst -> Risk Manager -> Executor pipeline using typed contracts.
4. **Risk hard gates**: directional signal, confidence >= 0.60, stop distance <= 2%, size <= US$500.
5. **IGP**: global and per-asset cooldowns to approximate serialised inference admission.
6. **Audit artefacts**: `pipeline_log`, `trades`, and `vol_history` written to CSV and SQLite.
7. **Cost sensitivity**: paper-style round-trip notional cost scenarios.

When full OHLCV input is supplied, approved trades use intrabar stop-loss and take-profit execution over future OHLC bars. If stop-loss and take-profit are both touched in the same candle, the simulator uses a conservative stop-loss-first tie-breaker because OHLCV does not reveal the intrabar path. Close-only inputs remain supported and fall back to deterministic fixed-horizon close exits.

## Important boundary

This is a **functional architecture replication**, not an empirical replication of the authors' five-day live dry-run.
It does not prove the reported 157 invocations, 139 trades, zero intervention, BTC benchmark, or CBD asset outcomes; those counts are generated for a new run rather than recovered from the original session.
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

The CSV must contain at least `timestamp,asset,close`. Full OHLCV input is also accepted with optional `open,high,low,volume` columns; when `high` and `low` are present, the executor uses stop-loss/take-profit exits instead of close-only fixed-horizon exits.

Downloaded market-data SQLite stores can be converted into replication input from the repository root:

```bash
python scripts/export_replication_input.py --db data/binanceusdm_ohlcv/market_data.sqlite --out data/binanceusdm_ohlcv/replication_input.csv
python scripts/export_replication_input.py --db data/binanceusdm_ohlcv/market_data.sqlite --out data/binanceusdm_ohlcv/replication_input_ohlcv.csv --format ohlcv
```

Exports include provenance columns such as `exchange_id`, `source_symbol`, and `timeframe` so generated `summary.json` and `replication_report.md` can report exchange and symbol coverage.

To build a larger complete-symbol universe, add `--complete-only` with the target window and optional `--symbol-limit`:

```bash
python ../scripts/export_replication_input.py --db ../data/binanceusdm_ohlcv_large/market_data.sqlite --exchange binanceusdm --format ohlcv --complete-only --start 2026-04-06T00:00:00Z --end 2026-04-11T23:59:59Z --symbol-limit 76 --required-symbol BTC/USDT:USDT --symbols-out ../data/binanceusdm_ohlcv_large/complete_symbols_76.txt --out ../data/binanceusdm_ohlcv_large/replication_input_ohlcv_76.csv
```

Compare a baseline run against a larger-universe run from the repository root:

```bash
python scripts/compare_replication_runs.py --baseline replication/results_real_binance_calibrated/summary.json --candidate replication/results_real_binance_large_76/summary.json --out docs/replication_large_universe_comparison.md
```

## Calibration Sweep

Use `sweep.py` to run an in-process calibration grid without writing per-run audit databases:

```bash
python sweep.py --config config.yaml --input-csv ../data/binanceusdm_ohlcv/replication_input_ohlcv.csv --out results_calibration_sweep
```

The default 36-run grid varies `igp.global_cooldown_seconds`, `azte.z_threshold`, `risk.confidence_gate`, and `azte.absolute_return_floor`, then ranks each run by normalized absolute error against the paper aggregate targets. Use `--grid-json` for a custom grid and `--max-runs` for quick smoke tests. Outputs are written to `calibration_sweep_results.csv` and `calibration_sweep_top10.md`.

## Outputs

- `results/agenticaita_replication.sqlite`
- `results/pipeline_log.csv`
- `results/trades.csv`
- `results/vol_history.csv`
- `results/summary.json`
- `results/replication_report.md`

`summary.json` includes a `metadata` block with the data source, candle and asset counts, per-asset coverage, config values, execution mode, and git commit SHA when available. The Markdown report includes the same information under `Run Metadata`.

## What this adds beyond the earlier claim audit

The earlier audit checked whether reported numbers were internally consistent. This harness checks whether the described
architecture can be made executable and auditable under the published equations and gates. It also creates the same class
of artefacts that would be needed to compare against the paper's claims.
