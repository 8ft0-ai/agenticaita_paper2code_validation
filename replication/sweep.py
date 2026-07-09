"""Run calibration sweeps for the AGENTICAITA replication harness."""
from __future__ import annotations

import argparse
import copy
import itertools
import json
from pathlib import Path
from typing import Iterable, Iterator

import pandas as pd
import yaml

from replicate import apply_llm_cli_overrides, configured_prompts, configured_volatility_regime
from src.agenticaita.agents import AnalystConfig
from src.agenticaita.agents_llm import LLMAnalyst, LLMRiskManager
from src.agenticaita.data import load_ohlcv_csv
from src.agenticaita.llm import build_llm_provider
from src.agenticaita.metrics import summarise
from src.agenticaita.risk import RiskConfig
from src.agenticaita.simulator import PipelineSimulator, SimulatorConfig


PAPER_TARGETS = {
    "total_invocations": 157.0,
    "trades_executed": 139.0,
    "agentic_friction_pct": 11.4649681529,
    "win_rate_pct": 51.7985611511,
    "profit_factor": 0.84093308,
    "net_pnl_usd": -15.07,
}

DEFAULT_GRID = {
    "igp.global_cooldown_seconds": [2400, 3000, 3600, 4200, 4800, 5400],
    "azte.z_threshold": [2.0, 2.25, 2.5],
    "risk.confidence_gate": [0.60, 0.65],
    "azte.absolute_return_floor": [0.003],
}

LLM_CLI_FLAGS = [
    ("--provider", {}),
    ("--model", {}),
    ("--temperature", {"type": float}),
    ("--max-tokens", {"type": int, "dest": "max_tokens"}),
    ("--timeout", {"type": float}),
    ("--base-url", {"dest": "base_url"}),
    ("--api-key-env", {"dest": "api_key_env"}),
    ("--audit-log", {"dest": "audit_log"}),
    ("--max-retries", {"type": int, "dest": "max_retries"}),
    ("--retry-backoff", {"type": float, "dest": "retry_backoff"}),
]


def load_config(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_grid(path: str | Path | None) -> dict[str, list]:
    if path is None:
        return copy.deepcopy(DEFAULT_GRID)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def iter_grid(grid: dict[str, list]) -> Iterator[dict[str, object]]:
    keys = list(grid)
    for values in itertools.product(*(grid[key] for key in keys)):
        yield dict(zip(keys, values))


def set_nested(cfg: dict, dotted_key: str, value: object) -> None:
    current = cfg
    parts = dotted_key.split(".")
    for part in parts[:-1]:
        current = current[part]
    current[parts[-1]] = value


def config_for_params(base_cfg: dict, params: dict[str, object]) -> dict:
    cfg = copy.deepcopy(base_cfg)
    for key, value in params.items():
        set_nested(cfg, key, value)
    return cfg


def build_simulator(cfg: dict, agents: str | None = None, prompt_dir: str | Path | None = None) -> PipelineSimulator:
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
    agent_cfg = copy.deepcopy(cfg.get("agents", {}))
    if agents is not None:
        agent_cfg.update({"analyst": agents, "risk_manager": agents})

    analyst_agent = risk_manager = None
    if "llm" in {agent_cfg.get("analyst"), agent_cfg.get("risk_manager")}:
        provider = build_llm_provider(cfg)
        prompts = configured_prompts(cfg, prompt_dir)
        regime_cfg = configured_volatility_regime(cfg)
        analyst_agent = (
            LLMAnalyst(provider, analyst_cfg, system_prompt=prompts["analyst_system_prompt"], volatility_regime_config=regime_cfg)
            if agent_cfg.get("analyst") == "llm"
            else None
        )
        risk_manager = (
            LLMRiskManager(provider, risk_cfg, system_prompt=prompts["risk_system_prompt"])
            if agent_cfg.get("risk_manager") == "llm"
            else None
        )

    return PipelineSimulator(
        sim_cfg,
        risk_cfg,
        analyst_cfg,
        analyst_agent=analyst_agent,
        risk_manager=risk_manager,
        episodic_memory_depth=int(agent_cfg.get("episodic_memory_depth", 0)),
    )


def metric_error(actual: float | None, target: float) -> float:
    if actual is None:
        return 1.0
    scale = abs(target) if abs(target) > 1e-12 else 1.0
    return abs(float(actual) - target) / scale


def alignment_score(summary: dict, targets: dict[str, float] = PAPER_TARGETS) -> tuple[float, dict[str, float]]:
    errors = {f"{metric}_error": metric_error(summary.get(metric), target) for metric, target in targets.items()}
    return sum(errors.values()) / len(errors), errors


def flatten_params(params: dict[str, object]) -> dict[str, object]:
    return {key.replace(".", "_"): value for key, value in params.items()}


def run_one(ohlcv: pd.DataFrame, base_cfg: dict, params: dict[str, object], agents: str = "deterministic", prompt_dir: str | Path | None = None) -> dict:
    cfg = config_for_params(base_cfg, params)
    pipeline_log, trades, _ = build_simulator(cfg, agents=agents, prompt_dir=prompt_dir).run(ohlcv)
    summary = summarise(pipeline_log, trades).to_dict()
    score, errors = alignment_score(summary)
    return {"alignment_score": score, **flatten_params(params), **summary, **errors}


def run_sweep(ohlcv: pd.DataFrame, base_cfg: dict, grid: dict[str, list], max_runs: int | None = None, agents: str = "deterministic", prompt_dir: str | Path | None = None) -> pd.DataFrame:
    rows = []
    params_iter: Iterable[dict[str, object]] = iter_grid(grid)
    if max_runs is not None:
        params_iter = itertools.islice(params_iter, max_runs)
    for params in params_iter:
        rows.append(run_one(ohlcv, base_cfg, params, agents=agents, prompt_dir=prompt_dir))
    return pd.DataFrame(rows).sort_values("alignment_score").reset_index(drop=True)


def write_outputs(results: pd.DataFrame, out_dir: Path, top_n: int, input_csv: str, grid: dict[str, list], agents: str = "deterministic") -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    results.to_csv(out_dir / "calibration_sweep_results.csv", index=False)
    top = results.head(top_n).copy()
    top.insert(0, "rank", range(1, len(top) + 1))
    lines = [
        "# Calibration Sweep Results",
        "",
        f"Input CSV: `{input_csv}`",
        f"Agent mode: `{agents}`",
        f"Run count: `{len(results)}`",
        "",
        "## Paper Targets",
        "",
        pd.DataFrame([PAPER_TARGETS]).to_markdown(index=False),
        "",
        "## Grid",
        "",
        pd.DataFrame([{"parameter": key, "values": ", ".join(str(value) for value in values)} for key, values in grid.items()]).to_markdown(index=False),
        "",
        f"## Top {min(top_n, len(top))}",
        "",
        top.to_markdown(index=False),
        "",
        "Lower `alignment_score` is better. Scores are normalized absolute errors against paper aggregate targets.",
        "These sweeps calibrate functional replication behavior and do not empirically reproduce the original live dry-run.",
    ]
    (out_dir / "calibration_sweep_top10.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--out", default="results_calibration_sweep")
    parser.add_argument("--grid-json", default=None, help="optional JSON object mapping dotted config keys to value lists")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--max-runs", type=int, default=None, help="optional cap for smoke-testing a subset of the grid")
    parser.add_argument("--agents", choices=["deterministic", "llm"], default="deterministic")
    for flag, kwargs in LLM_CLI_FLAGS:
        parser.add_argument(flag, default=None, help="Override LLM config value", **kwargs)
    parser.add_argument("--prompt-dir", default=None, help="Directory with analyst_system_prompt.txt and/or risk_system_prompt.txt")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    cfg = load_config(args.config)
    apply_llm_cli_overrides(cfg, args)
    grid = load_grid(args.grid_json)
    ohlcv = load_ohlcv_csv(args.input_csv)
    results = run_sweep(ohlcv, cfg, grid, max_runs=args.max_runs, agents=args.agents, prompt_dir=args.prompt_dir)
    write_outputs(results, Path(args.out), args.top_n, args.input_csv, grid, agents=args.agents)
    print(f"wrote {len(results)} ranked sweep runs to {args.out}")


if __name__ == "__main__":
    main()
