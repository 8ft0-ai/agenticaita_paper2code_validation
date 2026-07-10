"""Run a tiny LLM live-provider smoke check for AGENTICAITA.

The script is intentionally small and auditable. It creates a five-row input CSV,
writes a smoke-specific config, and invokes replicate.py with --agents llm. When
the configured API key is missing, the live provider is skipped and the LLM agent
wrappers exercise their deterministic fallback path instead of failing.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

SMOKE_PRICES = [100.0, 100.01, 100.02, 100.03, 101.0]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--out", default="results_llm_live_smoke")
    parser.add_argument("--api-key-env", default=None, help="Override the llm.api_key_env value for the smoke run")
    parser.add_argument("--model", default=None, help="Override the LLM model for the smoke run")
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument(
        "--skip-without-key",
        action="store_true",
        help="Exit 0 after writing smoke_status.json if the configured API key is absent",
    )
    return parser


def load_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def build_smoke_input(path: Path) -> pd.DataFrame:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        [
            {"timestamp": f"2026-04-06T00:0{index}:00Z", "asset": "BTC", "close": price}
            for index, price in enumerate(SMOKE_PRICES)
        ]
    )
    df.to_csv(path, index=False)
    return df


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_audit_marker(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def smoke_config(base_cfg: dict[str, Any], out_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    cfg = json.loads(json.dumps(base_cfg))
    cfg.setdefault("experiment", {})["output_dir"] = str(out_dir)
    cfg.setdefault("azte", {}).update({"rolling_window": 2, "z_threshold": 99.0, "absolute_return_floor": 0.003})
    cfg.setdefault("igp", {}).update({"global_cooldown_seconds": 0, "per_asset_cooldown_seconds": 0})
    cfg.setdefault("risk", {}).update({"confidence_gate": 0.0})
    cfg.setdefault("agents", {}).update({"analyst": "llm", "risk_manager": "llm", "episodic_memory_depth": 2})

    llm_cfg = cfg.setdefault("llm", {})
    llm_cfg["audit_log_path"] = str(out_dir / "llm_audit.jsonl")
    if args.api_key_env:
        llm_cfg["api_key_env"] = args.api_key_env
    if args.model:
        llm_cfg["model"] = args.model
    if args.temperature is not None:
        llm_cfg["temperature"] = args.temperature
    if args.max_tokens is not None:
        llm_cfg["max_tokens"] = args.max_tokens
    return cfg


def run_replicate(replication_root: Path, config_path: Path, input_path: Path, out_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "replicate.py",
            "--config",
            str(config_path),
            "--input-csv",
            str(input_path),
            "--out",
            str(out_dir),
            "--agents",
            "llm",
        ],
        cwd=replication_root,
        check=False,
        capture_output=True,
        text=True,
    )


def main() -> int:
    args = build_parser().parse_args()
    replication_root = Path(__file__).resolve().parent
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = smoke_config(load_config(Path(args.config)), out_dir, args)
    api_key_env = str(cfg.get("llm", {}).get("api_key_env", "OPENROUTER_API_KEY"))
    live_provider_available = bool(os.environ.get(api_key_env))
    audit_log = out_dir / "llm_audit.jsonl"
    status_path = out_dir / "smoke_status.json"

    base_status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "api_key_env": api_key_env,
        "live_provider_available": live_provider_available,
        "output_dir": str(out_dir),
    }

    if not live_provider_available and args.skip_without_key:
        status = {
            **base_status,
            "status": "skipped_missing_api_key",
            "reason": f"{api_key_env} is not set; live OpenRouter smoke was skipped",
        }
        write_json(status_path, status)
        append_audit_marker(audit_log, {"event": "live_provider_skipped", **status})
        print(status["reason"])
        return 0

    input_path = out_dir / "llm_live_smoke_input.csv"
    config_path = out_dir / "llm_live_smoke_config.yaml"
    build_smoke_input(input_path)
    config_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

    result = run_replicate(replication_root, config_path, input_path, out_dir)
    pipeline_path = out_dir / "pipeline_log.csv"

    status = {
        **base_status,
        "status": "live_provider_smoke" if live_provider_available else "fallback_without_api_key",
        "reason": "live provider used" if live_provider_available else f"{api_key_env} is not set; live provider skipped and deterministic fallback exercised",
        "input_csv": str(input_path),
        "config": str(config_path),
        "pipeline_log": str(pipeline_path),
        "audit_log": str(audit_log),
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }

    if result.returncode != 0:
        status["status"] = "failed"
        write_json(status_path, status)
        print(result.stderr or result.stdout, file=sys.stderr)
        return result.returncode

    if not audit_log.exists():
        append_audit_marker(audit_log, {"event": "live_provider_skipped", **status})

    if live_provider_available and audit_log.stat().st_size == 0:
        status["status"] = "failed_no_live_audit"
        write_json(status_path, status)
        print("Live smoke completed without a provider audit record.", file=sys.stderr)
        return 2

    if pipeline_path.exists():
        pipeline = pd.read_csv(pipeline_path)
        status["pipeline_rows"] = int(len(pipeline))
        status["agent_warning_rows"] = int(pipeline.get("agent_warnings", pd.Series(dtype=str)).fillna("").astype(str).str.len().gt(0).sum())
    else:
        status["pipeline_rows"] = 0

    write_json(status_path, status)
    print(f"{status['status']}: wrote smoke outputs to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
