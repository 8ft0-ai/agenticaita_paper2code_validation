from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_summary(tmp_path: Path, rows: list[dict]) -> str:
    root = Path(__file__).resolve().parents[1]
    index = tmp_path / "results_index.jsonl"
    output = tmp_path / "summary.md"
    index.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    subprocess.run([sys.executable, "scripts/write_github_step_summary.py", "--index", str(index), "--summary-file", "results_index.md", "--dashboard", "results_dashboard.html", "--out", str(output)], cwd=root, check=True, capture_output=True, text=True)
    return output.read_text(encoding="utf-8")


def test_summary_includes_status_counts_and_key_metrics(tmp_path: Path) -> None:
    summary = run_summary(
        tmp_path,
        [
            {"run_id": "validation", "scenario": "static_validation", "status": "warning", "quality_status": "not_run", "commit_sha": "abcdef123456", "warnings": ["unsupported results present: 1"], "artefacts": {"report": "validation/results/validation_report.md"}},
            {"run_id": "replication", "scenario": "replication", "status": "pass", "quality_status": "pass", "commit_sha": "abcdef123456", "data": {"asset_count": 15}, "metrics": {"trade_count": 4, "net_pnl_usd": 8.25}, "artefacts": {"summary_json": "replication/results/summary.json", "replication_report": "replication/results/replication_report.md"}},
        ],
    )
    assert "# Run results summary" in summary
    assert "| pass | 1 |" in summary
    assert "| warning | 1 |" in summary
    assert "abcdef12" in summary
    assert "static_validation" in summary
    assert "replication" in summary
    assert "15" in summary
    assert "4" in summary
    assert "8.25" in summary
    assert "summary_json" in summary
    assert "results_dashboard.html" in summary


def test_summary_handles_missing_optional_metrics(tmp_path: Path) -> None:
    summary = run_summary(tmp_path, [{"run_id": "minimal", "scenario": "quality_check", "status": "unknown", "quality_status": "unknown", "warnings": [], "artefacts": {}}])
    assert "quality_check" in summary
    assert "| unknown | 1 |" in summary
    assert "No index or dashboard paths" not in summary


def test_summary_escapes_pipes_and_includes_warnings(tmp_path: Path) -> None:
    summary = run_summary(tmp_path, [{"run_id": "run|one", "scenario": "static_validation", "status": "warning", "quality_status": "not_run", "warnings": ["a|b"], "artefacts": {"report": "validation/results/validation_report.md"}}])
    assert "run\\|one" in summary
    assert "a\\|b" in summary
    assert "report" in summary


def test_summary_represents_invalid_jsonl_line_as_warning(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    index = tmp_path / "results_index.jsonl"
    output = tmp_path / "summary.md"
    index.write_text("{not valid json\n", encoding="utf-8")
    subprocess.run([sys.executable, "scripts/write_github_step_summary.py", "--index", str(index), "--out", str(output)], cwd=root, check=True, capture_output=True, text=True)
    summary = output.read_text(encoding="utf-8")
    assert "invalid JSONL line 1" in summary
    assert "| warning | 1 |" in summary
