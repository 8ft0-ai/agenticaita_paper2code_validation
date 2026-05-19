from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def render_dashboard(tmp_path: Path, rows: list[dict]) -> str:
    root = Path(__file__).resolve().parents[1]
    index = tmp_path / "results_index.jsonl"
    output = tmp_path / "results_dashboard.html"
    index.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "scripts/render_results_dashboard.py", "--index", str(index), "--out", str(output)],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "rendered" in result.stdout
    return output.read_text(encoding="utf-8")


def test_dashboard_renders_summary_cards_and_grouped_sections(tmp_path: Path) -> None:
    html = render_dashboard(
        tmp_path,
        [
            {"run_id": "validation-results", "scenario": "static_validation", "status": "warning", "quality_status": "not_run", "metrics": {"status_counts": {"pass": 2, "unsupported": 1}}, "artefacts": {"report": "validation/results/validation_report.md"}, "warnings": ["unsupported results present: 1"]},
            {"run_id": "replication-real", "scenario": "replication", "status": "pass", "quality_status": "pass", "data": {"asset_count": 15}, "metrics": {"trade_count": 4, "net_pnl_usd": 8.25}, "artefacts": {"summary_json": "replication/results/summary.json", "replication_report": "replication/results/replication_report.md"}, "warnings": []},
        ],
    )

    assert "Run Results Dashboard" in html
    assert "Static validation" in html
    assert "Replication" in html
    assert "validation_report.md" in html
    assert "replication_report.md" in html
    assert "warning" in html
    assert "pass" in html


def test_dashboard_includes_visual_summaries_for_status_symbols_and_trades(tmp_path: Path) -> None:
    html = render_dashboard(
        tmp_path,
        [
            {"run_id": "coverage", "scenario": "market_data_coverage", "status": "warning", "quality_status": "not_run", "metrics": {"symbol_count": 15, "complete_symbols": 12}, "warnings": ["incomplete symbols: 3"], "artefacts": {"coverage_report": "data/run/coverage_report.md"}},
            {"run_id": "replication", "scenario": "replication", "status": "pass", "quality_status": "pass", "metrics": {"trade_count": 7, "net_pnl_usd": -3.5}, "warnings": [], "artefacts": {}},
        ],
    )

    assert "Status summary" in html
    assert "Symbol coverage" in html
    assert "coverage: 12 / 15" in html
    assert "Trade and PnL summary" in html
    assert "-3.5" in html


def test_dashboard_handles_missing_optional_metrics(tmp_path: Path) -> None:
    html = render_dashboard(
        tmp_path,
        [{"run_id": "minimal", "scenario": "quality_check", "status": "unknown", "quality_status": "unknown", "warnings": [], "artefacts": {}}],
    )

    assert "Quality checks" in html
    assert "No symbol coverage metrics were present." in html
    assert "No trade or PnL metrics were present." in html


def test_dashboard_represents_invalid_jsonl_line_as_warning(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    index = tmp_path / "results_index.jsonl"
    output = tmp_path / "results_dashboard.html"
    index.write_text("{not valid json\n", encoding="utf-8")

    subprocess.run(
        [sys.executable, "scripts/render_results_dashboard.py", "--index", str(index), "--out", str(output)],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )

    html = output.read_text(encoding="utf-8")
    assert "invalid JSONL line 1" in html
    assert "Unknown" in html
