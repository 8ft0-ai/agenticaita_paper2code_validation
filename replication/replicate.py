"""Run a functional AGENTICAITA replication harness."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pandas as pd
import yaml

from src.agenticaita.data import generate_synthetic_ohlcv, load_ohlcv_csv
from src.agenticaita.metrics import funding_accounting, summarise, transaction_cost_sensitivity
from src.agenticaita.risk import RiskConfig
from src.agenticaita.agents import AnalystConfig
from src.agenticaita.simulator import PipelineSimulator, SimulatorConfig, write_sqlite


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def get_git_commit_sha(repo_root: Path | None = None) -> str | None:
    repo_root = repo_root or Path(__file__).resolve().parents[1]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    sha = result.stdout.strip()
    return sha or None


def build_config_metadata(cfg: dict) -> dict:
    return {
        "experiment": {key: cfg["experiment"].get(key) for key in ("name", "mode", "seed") if key in cfg["experiment"]},
        "azte": dict(cfg["azte"]),
        "igp": dict(cfg["igp"]),
        "risk": dict(cfg["risk"]),
        "cbd": dict(cfg["cbd"]),
        "cost_scenarios": dict(cfg["cost_scenarios"]),
        "synthetic_data": dict(cfg.get("synthetic_data", {})),
    }


def build_data_metadata(ohlcv: pd.DataFrame, data_source: str) -> dict:
    assets = sorted(str(asset) for asset in ohlcv["asset"].dropna().unique()) if "asset" in ohlcv else []
    per_asset_counts = {str(asset): int(count) for asset, count in ohlcv.groupby("asset").size().sort_index().items()} if "asset" in ohlcv else {}
    metadata: dict = {
        "data_source": data_source,
        "columns": list(ohlcv.columns),
        "candle_count": int(len(ohlcv)),
        "asset_count": len(assets),
        "assets": assets,
        "per_asset_candle_counts": per_asset_counts,
    }
    if "source_symbol" in ohlcv:
        metadata["source_symbols"] = sorted(str(symbol) for symbol in ohlcv["source_symbol"].dropna().unique())
    if "exchange_id" in ohlcv:
        metadata["exchange_ids"] = sorted(str(exchange) for exchange in ohlcv["exchange_id"].dropna().unique())
    if "timeframe" in ohlcv:
        metadata["timeframes"] = sorted(str(timeframe) for timeframe in ohlcv["timeframe"].dropna().unique())
    if "funding_rate" in ohlcv:
        funding = ohlcv.dropna(subset=["funding_rate"])
        metadata["funding"] = {
            "funding_rate_column": True,
            "funding_rows": int(len(funding)),
            "funding_rows_by_asset": {str(asset): int(count) for asset, count in funding.groupby("asset").size().sort_index().items()},
            "assets_without_funding_rows": sorted(str(asset) for asset in set(assets) - set(str(asset) for asset in funding["asset"].dropna().unique())),
        }
    else:
        metadata["funding"] = {"funding_rate_column": False, "status": "unsupported"}
    if not ohlcv.empty and "timestamp" in ohlcv:
        metadata["start_timestamp"] = str(ohlcv["timestamp"].min())
        metadata["end_timestamp"] = str(ohlcv["timestamp"].max())
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--input-csv", default=None, help="Optional OHLCV CSV with timestamp,asset,close columns")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    out_dir = Path(args.out or cfg["experiment"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.input_csv:
        ohlcv = load_ohlcv_csv(args.input_csv)
        data_source = args.input_csv
    else:
        synth = cfg["synthetic_data"]
        ohlcv = generate_synthetic_ohlcv(
            synth["assets"],
            minutes=int(synth["minutes"]),
            seed=int(cfg["experiment"]["seed"]),
            macro_shock_minute=int(synth["macro_shock_minute"]),
            macro_shock_size=float(synth["macro_shock_size"]),
        )
        data_source = "deterministic_synthetic"

    sim_cfg = SimulatorConfig(
        rolling_window=int(cfg["azte"]["rolling_window"]),
        z_threshold=float(cfg["azte"]["z_threshold"]),
        absolute_return_floor=float(cfg["azte"]["absolute_return_floor"]),
        global_cooldown_seconds=int(cfg["igp"]["global_cooldown_seconds"]),
        per_asset_cooldown_seconds=int(cfg["igp"]["per_asset_cooldown_seconds"]),
        benchmark_asset=str(cfg["cbd"]["benchmark_asset"]),
        cbd_alpha=float(cfg["cbd"]["alpha"]),
        cbd_kappa=float(cfg["cbd"]["kappa"]),
        transaction_cost_rate=0.0,
    )
    risk_cfg = RiskConfig(
        confidence_gate=float(cfg["risk"]["confidence_gate"]),
        max_stop_loss_fraction=float(cfg["risk"]["max_stop_loss_fraction"]),
        max_position_size_usd=float(cfg["risk"]["max_position_size_usd"]),
    )
    analyst_cfg = AnalystConfig(base_position_size_usd=float(cfg["risk"]["base_position_size_usd"]))
    simulator = PipelineSimulator(sim_cfg, risk_cfg, analyst_cfg)
    pipeline_log, trades, vol_history = simulator.run(ohlcv)
    summary = summarise(pipeline_log, trades)

    ohlcv.to_csv(out_dir / "ohlcv_used.csv", index=False)
    pipeline_log.to_csv(out_dir / "pipeline_log.csv", index=False)
    trades.to_csv(out_dir / "trades.csv", index=False)
    vol_history.to_csv(out_dir / "vol_history.csv", index=False)
    write_sqlite(out_dir / "agenticaita_replication.sqlite", pipeline_log, trades, vol_history)

    total_notional = float(trades["size_usd"].sum()) if not trades.empty else 0.0
    costs = transaction_cost_sensitivity(summary.net_pnl_usd, total_notional, cfg["cost_scenarios"])
    funding = funding_accounting(ohlcv, trades)
    report = {
        "data_source": data_source,
        "replication_level": "functional architecture replication, not empirical replication",
        "execution": {
            "execution_model": simulator.execution_model,
            "exit_horizon_minutes": sim_cfg.exit_horizon_minutes,
            "intrabar_tie_breaker": "stop_loss_first",
            "stop_take_profit_enabled": simulator.execution_model == "ohlcv_intrabar_stop_take_profit",
        },
        "metadata": {
            "git_commit_sha": get_git_commit_sha(),
            "config": build_config_metadata(cfg),
            "data": build_data_metadata(ohlcv, data_source),
            "execution": {
                "execution_model": simulator.execution_model,
                "exit_horizon_minutes": sim_cfg.exit_horizon_minutes,
                "intrabar_tie_breaker": "stop_loss_first",
                "stop_take_profit_enabled": simulator.execution_model == "ohlcv_intrabar_stop_take_profit",
            },
        },
        "summary": summary.to_dict(),
        "benchmark_modes": funding,
        "transaction_cost_sensitivity": costs,
        "caveat": "Synthetic data and deterministic proxy agents do not validate the paper's live-market claims.",
    }
    (out_dir / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = [
        "# AGENTICAITA functional replication run",
        "",
        f"Data source: `{data_source}`",
        "",
        "This run executes the paper's published architecture in dry-run form: AZTE trigger, CBD score, sequential analyst/risk/executor pipeline, deterministic risk gates, IGP cooldowns, SQLite audit tables, and transaction-cost sensitivity.",
        "",
        "It is not an empirical replication unless supplied with the author's raw market data, order-book/funding snapshots, exact prompts, LLM outputs, and SQLite logs.",
        "",
        "## Run Metadata",
        "",
        "```json",
        json.dumps(report["metadata"], indent=2),
        "```",
        "",
        "## Execution Model",
        "",
        "```json",
        json.dumps(report["execution"], indent=2),
        "```",
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(summary.to_dict(), indent=2),
        "```",
        "",
        "## Benchmark Modes",
        "",
        "```json",
        json.dumps(funding, indent=2),
        "```",
        "",
        "## Transaction-cost sensitivity",
        "",
        pd.DataFrame(costs).to_markdown(index=False),
    ]
    (out_dir / "replication_report.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
