from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_manifest(tmp_path: Path, *args: str) -> dict:
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "run_manifest.json"
    result = subprocess.run([sys.executable, "scripts/build_run_manifest.py", *args, "--out", str(out), "--base-dir", str(tmp_path)], cwd=root, check=True, capture_output=True, text=True)
    assert str(out) in result.stdout
    return json.loads(out.read_text(encoding="utf-8"))


def test_static_validation_manifest_counts_statuses(tmp_path: Path) -> None:
    run_dir = tmp_path / "validation" / "results"
    run_dir.mkdir(parents=True)
    (run_dir / "validation_results.json").write_text(json.dumps([{"status": "pass"}, {"status": "unsupported"}]), encoding="utf-8")
    (run_dir / "validation_report.md").write_text("# report\n", encoding="utf-8")

    manifest = run_manifest(tmp_path, "--run-dir", str(run_dir), "--scenario", "static_validation", "--commit-sha", "abc123")

    assert manifest["scenario"] == "static_validation"
    assert manifest["commit_sha"] == "abc123"
    assert manifest["status"] == "warning"
    assert manifest["metrics"]["status_counts"] == {"pass": 1, "unsupported": 1}
    assert manifest["artefacts"]["report"] == "validation/results/validation_report.md"


def test_replication_manifest_reads_summary_and_relative_paths(tmp_path: Path) -> None:
    run_dir = tmp_path / "replication" / "results_real_binanceusdm_real_subset"
    run_dir.mkdir(parents=True)
    (run_dir / "summary.json").write_text(json.dumps({"metadata": {"data": {"asset_count": 15, "candle_count": 4320}}, "summary": {"trade_count": 3, "net_pnl_usd": 12.5}}), encoding="utf-8")
    (run_dir / "replication_report.md").write_text("# report\n", encoding="utf-8")

    manifest = run_manifest(tmp_path, "--run-dir", str(run_dir), "--scenario", "replication")

    assert manifest["status"] == "pass"
    assert manifest["data"]["asset_count"] == 15
    assert manifest["metrics"]["trade_count"] == 3
    assert manifest["artefacts"]["summary_json"] == "replication/results_real_binanceusdm_real_subset/summary.json"


def test_quality_manifest_promotes_warning_status(tmp_path: Path) -> None:
    run_dir = tmp_path / "quality"
    run_dir.mkdir()
    (run_dir / "quality_report.json").write_text(json.dumps({"status": "pass", "warnings": ["trades.csv is empty"], "input": {"rows": 10}}), encoding="utf-8")

    manifest = run_manifest(tmp_path, "--run-dir", str(run_dir), "--scenario", "quality_check")

    assert manifest["status"] == "warning"
    assert manifest["quality_status"] == "warning"
    assert manifest["metrics"]["input_rows"] == 10


def test_unknown_manifest_warns_instead_of_crashing(tmp_path: Path) -> None:
    run_dir = tmp_path / "empty_run"
    run_dir.mkdir()

    manifest = run_manifest(tmp_path, "--run-dir", str(run_dir))

    assert manifest["scenario"] == "unknown"
    assert manifest["status"] == "warning"
    assert manifest["warnings"] == ["could not infer run scenario from available artefacts"]
