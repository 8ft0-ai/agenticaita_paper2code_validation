from __future__ import annotations

import json

from scripts.compare_replication_to_paper import build_rows, read_trade_metrics, write_markdown


def make_report() -> dict:
    return {
        "data_source": "fixture.csv",
        "metadata": {
            "data": {"asset_count": 3, "candle_count": 300, "start_timestamp": "2026-04-06 00:00:00+00:00", "end_timestamp": "2026-04-06 01:39:00+00:00"},
            "execution": {"execution_model": "ohlcv_intrabar_stop_take_profit"},
            "config": {"agents": {"analyst": "deterministic"}, "azte": {"z_threshold": 2.0}, "cbd": {"alpha": 0.5}, "risk": {"confidence_gate": 0.65}},
        },
        "summary": {
            "total_invocations": 157,
            "analyst_long": 142,
            "analyst_short": 2,
            "analyst_wait": 13,
            "risk_approved": 139,
            "risk_rejected": 5,
            "trades_executed": 139,
            "wins": 72,
            "losses": 67,
            "gross_profit_usd": 79.67,
            "gross_loss_usd_abs": 94.74,
            "net_pnl_usd": -15.07,
            "win_rate_pct": 52.5,
            "profit_factor": 0.84,
            "agentic_friction_pct": 12.0,
        },
    }


def test_build_rows_classifies_exact_approximate_and_unavailable() -> None:
    rows = build_rows(make_report(), {"unique_traded_assets": 76, "total_notional_usd": 26079.0})
    by_metric = {row["metric"]: row for row in rows}

    assert by_metric["total_invocations"]["classification"] == "exact"
    assert by_metric["win_rate_pct"]["classification"] == "approximate"
    assert by_metric["reported_alpha_usd"]["classification"] == "unavailable"


def test_read_trade_metrics_counts_assets_and_notional(tmp_path) -> None:
    trades = tmp_path / "trades.csv"
    trades.write_text("asset,size_usd\nBTC,100\nETH,50.5\nBTC,25\n", encoding="utf-8")

    metrics = read_trade_metrics(trades)

    assert metrics == {"unique_traded_assets": 2, "total_notional_usd": 175.5}


def test_write_markdown_gap_report_includes_limitations(tmp_path) -> None:
    out = tmp_path / "gap.md"
    rows = build_rows(make_report(), {"unique_traded_assets": 76, "total_notional_usd": 26079.0})

    write_markdown(rows, make_report(), "summary.json", "trades.csv", out)

    content = out.read_text(encoding="utf-8")
    assert "# AGENTICAITA Paper Replication Gap Report" in content
    assert "Paper Baseline Comparison" in content
    assert "original L2 order book snapshots" in content
    assert "BTC benchmark alpha USD" in content


def test_markdown_report_is_json_serialisable_context_safe(tmp_path) -> None:
    report = make_report()
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps(report), encoding="utf-8")

    rows = build_rows(report)

    assert any(row["classification"] == "unavailable" for row in rows)
