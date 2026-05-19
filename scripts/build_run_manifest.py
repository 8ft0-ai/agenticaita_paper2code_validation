#!/usr/bin/env python3
"""Build a standard run_manifest.json for generated repository runs."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1"
SCENARIOS = ("auto", "static_validation", "real_data_validation", "replication", "quality_check", "market_data_coverage", "unknown")


def read_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def rel(path: Path, base: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path)


def add_artifact(manifest: dict[str, Any], key: str, path: Path, base: Path, *, required: bool = False) -> None:
    if path.exists():
        manifest["artefacts"][key] = rel(path, base)
    elif required:
        manifest["missing_artefacts"].append(path.name)


def status_from_counts(counts: Counter[str]) -> str:
    if counts.get("fail") or counts.get("error"):
        return "fail"
    if any(counts.get(s) for s in ("qualified", "unsupported", "exploratory", "warning", "partial")):
        return "warning"
    if counts and counts.get("pass") == sum(counts.values()):
        return "pass"
    return "unknown"


def warn_status(status: str, warnings: list[str]) -> str:
    return "warning" if warnings and status in {"pass", "unknown"} else status


def detect(run_dir: Path, quality_json: Path | None) -> str:
    checks = [
        (quality_json is not None or (run_dir / "quality_report.json").exists(), "quality_check"),
        ((run_dir / "summary.json").exists(), "replication"),
        ((run_dir / "real_data_validation_results.json").exists(), "real_data_validation"),
        ((run_dir / "validation_results.json").exists(), "static_validation"),
        ((run_dir / "coverage_report.json").exists(), "market_data_coverage"),
    ]
    return next((scenario for ok, scenario in checks if ok), "unknown")


def new_manifest(args: argparse.Namespace, scenario: str) -> dict[str, Any]:
    run_dir = Path(args.run_dir)
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": args.run_id or run_dir.name,
        "scenario": scenario,
        "commit_sha": args.commit_sha,
        "command": args.command,
        "started_at": args.started_at,
        "completed_at": args.completed_at,
        "status": "unknown",
        "quality_status": "not_run",
        "data": {},
        "metrics": {},
        "warnings": [],
        "artefacts": {},
        "missing_artefacts": [],
    }


def add_validation(run_dir: Path, manifest: dict[str, Any], base: Path, *, real: bool) -> None:
    stem = "real_data_validation" if real else "validation"
    rows = read_json(run_dir / f"{stem}_results.json", [])
    if not isinstance(rows, list):
        raise ValueError(f"{stem}_results.json must contain a JSON array")
    counts = Counter(str(row.get("status", "unknown")) for row in rows)
    manifest["status"] = status_from_counts(counts)
    manifest["metrics"] = {"result_count": len(rows), "status_counts": dict(sorted(counts.items()))}
    if real:
        sections = Counter(str(row.get("section", "unknown")) for row in rows)
        manifest["metrics"]["section_counts"] = dict(sorted(sections.items()))
    manifest["warnings"] += [f"{k} results present: {v}" for k, v in sorted(counts.items()) if k in {"qualified", "unsupported", "exploratory", "warning"}]
    add_artifact(manifest, "results_json", run_dir / f"{stem}_results.json", base, required=True)
    add_artifact(manifest, "results_csv", run_dir / f"{stem}_results.csv", base)
    add_artifact(manifest, "report", run_dir / f"{stem}_report.md", base)


def add_replication(run_dir: Path, manifest: dict[str, Any], base: Path) -> None:
    summary = read_json(run_dir / "summary.json", {})
    if not isinstance(summary, dict):
        raise ValueError("summary.json must contain a JSON object")
    data = summary.get("metadata", {}).get("data", {}) if isinstance(summary.get("metadata"), dict) else {}
    metrics = summary.get("summary", {}) if isinstance(summary.get("summary"), dict) else {}
    manifest["data"] = {k: data[k] for k in ("data_source", "asset_count", "candle_count", "start_timestamp", "end_timestamp") if k in data}
    manifest["metrics"] = {k: metrics[k] for k in ("trade_count", "approved_trades", "rejected_trades", "net_pnl_usd", "total_pnl_usd", "win_rate") if k in metrics}
    quality = summary.get("quality_checks", {}).get("outputs", {}) if isinstance(summary.get("quality_checks"), dict) else {}
    manifest["warnings"] += [str(w) for w in quality.get("warnings", [])] if isinstance(quality.get("warnings", []), list) else []
    manifest["quality_status"] = str(quality.get("status", "not_run")) if quality else "not_run"
    manifest["status"] = "warning" if manifest["warnings"] else "pass"
    for key, name, required in [("summary_json", "summary.json", True), ("replication_report", "replication_report.md", True), ("pipeline_log", "pipeline_log.csv", False), ("trades_csv", "trades.csv", False), ("sqlite", "agenticaita_replication.sqlite", False)]:
        add_artifact(manifest, key, run_dir / name, base, required=required)


def add_quality(run_dir: Path, manifest: dict[str, Any], base: Path, quality_json: Path | None) -> None:
    path = quality_json or run_dir / "quality_report.json"
    quality = read_json(path, {})
    if not isinstance(quality, dict):
        raise ValueError("quality JSON must contain an object")
    warnings = [str(w) for w in quality.get("warnings", [])] if isinstance(quality.get("warnings", []), list) else []
    manifest["warnings"] = warnings
    manifest["status"] = warn_status(str(quality.get("status", "unknown")), warnings)
    manifest["quality_status"] = manifest["status"]
    manifest["metrics"] = {"warning_count": len(warnings)}
    if isinstance(quality.get("input"), dict):
        manifest["metrics"]["input_rows"] = quality["input"].get("rows")
    add_artifact(manifest, "quality_json", path, base, required=True)


def add_coverage(run_dir: Path, manifest: dict[str, Any], base: Path) -> None:
    report = read_json(run_dir / "coverage_report.json", {})
    symbols = report.get("symbols", []) if isinstance(report.get("symbols"), list) else []
    incomplete = report.get("incomplete_symbols", []) if isinstance(report.get("incomplete_symbols"), list) else []
    manifest["data"] = {k: report.get(k) for k in ("exchange", "timeframe", "start", "end")}
    manifest["metrics"] = {"symbol_count": len(symbols), "complete_symbols": len([s for s in symbols if isinstance(s, dict) and s.get("complete")]), "incomplete_symbols": len(incomplete)}
    manifest["warnings"] = [f"incomplete symbols: {len(incomplete)}"] if incomplete else []
    manifest["status"] = "warning" if incomplete else "pass"
    add_artifact(manifest, "coverage_json", run_dir / "coverage_report.json", base, required=True)
    add_artifact(manifest, "coverage_report", run_dir / "coverage_report.md", base)


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    run_dir, base = Path(args.run_dir), Path(args.base_dir)
    quality_json = Path(args.quality_json) if args.quality_json else None
    scenario = args.scenario if args.scenario != "auto" else detect(run_dir, quality_json)
    manifest = new_manifest(args, scenario)
    if scenario == "static_validation":
        add_validation(run_dir, manifest, base, real=False)
    elif scenario == "real_data_validation":
        add_validation(run_dir, manifest, base, real=True)
    elif scenario == "replication":
        add_replication(run_dir, manifest, base)
    elif scenario == "quality_check":
        add_quality(run_dir, manifest, base, quality_json)
    elif scenario == "market_data_coverage":
        add_coverage(run_dir, manifest, base)
    else:
        manifest["warnings"].append("could not infer run scenario from available artefacts")
        manifest["status"] = "warning"
    if manifest["missing_artefacts"]:
        manifest["warnings"].append("missing artefacts: " + ", ".join(manifest["missing_artefacts"]))
    manifest["status"] = warn_status(str(manifest["status"]), manifest["warnings"])
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--scenario", choices=SCENARIOS, default="auto")
    parser.add_argument("--out", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--commit-sha", default=None)
    parser.add_argument("--command", default=None)
    parser.add_argument("--started-at", default=None)
    parser.add_argument("--completed-at", default=None)
    parser.add_argument("--quality-json", default=None)
    parser.add_argument("--base-dir", default=".")
    args = parser.parse_args(argv)
    out = Path(args.out) if args.out else Path(args.run_dir) / "run_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_manifest(args), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
