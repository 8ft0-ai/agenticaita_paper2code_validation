from __future__ import annotations

import json

from scripts.compare_replication_runs import build_comparison, load_summary, write_markdown


def make_report(asset_count: int, candles: int, invocations: int, trades: int, net_pnl: float) -> dict:
    return {
        "metadata": {
            "data": {"asset_count": asset_count, "candle_count": candles},
            "execution": {"execution_model": "ohlcv_intrabar_stop_take_profit"},
        },
        "summary": {
            "total_invocations": invocations,
            "trades_executed": trades,
            "risk_approved": trades,
            "risk_rejected": invocations - trades,
            "agentic_friction_pct": 10.0,
            "win_rate_pct": 50.0,
            "profit_factor": 0.9,
            "net_pnl_usd": net_pnl,
        },
    }


def test_build_comparison_includes_metric_deltas() -> None:
    comparison = build_comparison(make_report(15, 129600, 169, 153, -9.0), make_report(76, 656640, 220, 190, -20.0))

    row = comparison[comparison["metric"] == "asset_count"].iloc[0]
    assert row["baseline"] == 15
    assert row["candidate"] == 76
    assert row["delta"] == 61


def test_write_markdown_comparison(tmp_path) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    out = tmp_path / "comparison.md"
    baseline.write_text(json.dumps(make_report(15, 129600, 169, 153, -9.0)), encoding="utf-8")
    candidate.write_text(json.dumps(make_report(76, 656640, 220, 190, -20.0)), encoding="utf-8")

    comparison = build_comparison(load_summary(baseline), load_summary(candidate))
    write_markdown(comparison, str(baseline), str(candidate), out)

    content = out.read_text(encoding="utf-8")
    assert "# Replication Run Comparison" in content
    assert "asset_count" in content
    assert "total_invocations" in content
