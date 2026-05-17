#!/usr/bin/env python3
"""Compare two replication summary JSON files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


METRICS = (
    "asset_count",
    "candle_count",
    "total_invocations",
    "trades_executed",
    "risk_approved",
    "risk_rejected",
    "agentic_friction_pct",
    "win_rate_pct",
    "profit_factor",
    "net_pnl_usd",
    "execution_model",
)


def load_summary(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def metric_value(report: dict, metric: str):
    if metric in {"asset_count", "candle_count"}:
        return report.get("metadata", {}).get("data", {}).get(metric)
    if metric == "execution_model":
        return report.get("metadata", {}).get("execution", {}).get(metric) or report.get("execution", {}).get(metric)
    return report.get("summary", {}).get(metric)


def build_comparison(baseline: dict, candidate: dict) -> pd.DataFrame:
    rows = []
    for metric in METRICS:
        base = metric_value(baseline, metric)
        cand = metric_value(candidate, metric)
        delta = cand - base if isinstance(base, (int, float)) and isinstance(cand, (int, float)) else ""
        rows.append({"metric": metric, "baseline": base if base is not None else "", "candidate": cand if cand is not None else "", "delta": delta})
    return pd.DataFrame(rows, dtype=object)


def write_markdown(comparison: pd.DataFrame, baseline_path: str, candidate_path: str, out_path: str | Path) -> None:
    lines = [
        "# Replication Run Comparison",
        "",
        f"Baseline: `{baseline_path}`",
        f"Candidate: `{candidate_path}`",
        "",
        comparison.to_markdown(index=False),
        "",
        "This comparison checks whether calibrated functional replication behavior remains stable across a larger public market universe. It does not empirically reproduce the original live dry-run without the authors' artefacts.",
    ]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, help="baseline replication summary.json")
    parser.add_argument("--candidate", required=True, help="larger-universe replication summary.json")
    parser.add_argument("--out", required=True, help="output Markdown comparison path")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    comparison = build_comparison(load_summary(args.baseline), load_summary(args.candidate))
    write_markdown(comparison, args.baseline, args.candidate, args.out)
    print(f"wrote comparison to {args.out}")


if __name__ == "__main__":
    main()
