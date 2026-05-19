from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_index(tmp_path: Path, *patterns: str) -> tuple[list[dict], str]:
    root = Path(__file__).resolve().parents[1]
    out_jsonl = tmp_path / "results_index.jsonl"
    out_md = tmp_path / "results_index.md"
    subprocess.run(
        [sys.executable, "scripts/index_run_results.py", "--runs", *patterns, "--out-jsonl", str(out_jsonl), "--out-md", str(out_md), "--base-dir", str(tmp_path)],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    rows = [json.loads(line) for line in out_jsonl.read_text(encoding="utf-8").splitlines()]
    return rows, out_md.read_text(encoding="utf-8")


def test_index_static_validation_run(tmp_path: Path) -> None:
    run_dir = tmp_path / "validation" / "results"
    run_dir.mkdir(parents=True)
    (run_dir / "validation_results.json").write_text(json.dumps([{"status": "pass"}, {"status": "unsupported"}]), encoding="utf-8")
    (run_dir / "validation_report.md").write_text("# report\n", encoding="utf-8")

    rows, markdown = run_index(tmp_path, str(run_dir))

    assert len(rows) == 1
    assert rows[0]["scenario"] == "static_validation"
    assert rows[0]["status"] == "warning"
    assert rows[0]["metrics"]["status_counts"] == {"pass": 1, "unsupported": 1}
    assert "validation_report.md" in markdown


def test_index_replication_summary_run(tmp_path: Path) -> None:
    run_dir = tmp_path / "replication" / "results_real_binanceusdm_real_subset"
    run_dir.mkdir(parents=True)
    (run_dir / "summary.json").write_text(json.dumps({"metadata": {"data": {"asset_count": 15, "candle_count": 4320}}, "summary": {"trade_count": 4, "net_pnl_usd": 8.25}}), encoding="utf-8")
    (run_dir / "replication_report.md").write_text("# report\n", encoding="utf-8")

    rows, markdown = run_index(tmp_path, str(run_dir))

    assert rows[0]["scenario"] == "replication"
    assert rows[0]["metrics"]["trade_count"] == 4
    assert rows[0]["metrics"]["net_pnl_usd"] == 8.25
    assert "results_real_binanceusdm_real_subset" in markdown


def test_index_quality_warning_run(tmp_path: Path) -> None:
    run_dir = tmp_path / "quality"
    run_dir.mkdir()
    (run_dir / "quality_report.json").write_text(json.dumps({"status": "pass", "warnings": ["trades.csv is empty"], "input": {"rows": 9}}), encoding="utf-8")

    rows, markdown = run_index(tmp_path, str(run_dir))

    assert rows[0]["scenario"] == "quality_check"
    assert rows[0]["status"] == "warning"
    assert "trades.csv is empty" in markdown


def test_index_malformed_manifest_as_warning_entry(tmp_path: Path) -> None:
    run_dir = tmp_path / "broken"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text("{not valid json", encoding="utf-8")

    rows, markdown = run_index(tmp_path, str(run_dir))

    assert rows[0]["scenario"] == "unknown"
    assert rows[0]["status"] == "warning"
    assert "could not parse run directory" in rows[0]["warnings"][0]
    assert "could not parse run directory" in markdown
