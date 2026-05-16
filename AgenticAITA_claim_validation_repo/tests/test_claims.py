from __future__ import annotations

from math import isclose

from metrics import (
    cbd_score,
    cbd_z_tilde,
    run_all_validations,
    validate_binomial,
    validate_pipeline_counts,
    validate_trading_metrics,
)


def test_pipeline_friction_passes() -> None:
    results = {r.claim_id: r for r in validate_pipeline_counts()}
    assert results["pipeline.agentic_friction"].status == "pass"
    assert isclose(results["pipeline.agentic_friction"].computed_value, 11.464968, abs_tol=1e-6)


def test_trading_core_metrics_pass() -> None:
    results = {r.claim_id: r for r in validate_trading_metrics()}
    for claim_id in [
        "trading.win_rate_pct",
        "trading.net_pnl",
        "trading.profit_factor",
        "trading.risk_reward",
        "trading.break_even_win_rate",
        "trading.alpha_percentage_points",
    ]:
        assert results[claim_id].status == "pass", claim_id


def test_binomial_exact_is_qualified_not_failed() -> None:
    results = {r.claim_id: r for r in validate_binomial()}
    assert results["stats.binomial_pvalue_normal_approx"].status == "pass"
    assert results["stats.binomial_pvalue_exact_one_sided"].status == "qualified"
    assert results["stats.binomial_significance"].status == "pass"


def test_cbd_properties() -> None:
    assert cbd_z_tilde(1.9) == 0.0
    assert 0.0 <= cbd_z_tilde(2.0) < 1.0
    assert 0.0 <= cbd_z_tilde(10.0) < 1.0
    assert cbd_score(3.0, 0.9) > cbd_score(3.0, 0.1)


def test_no_unexpected_failures() -> None:
    results = run_all_validations()
    assert not [r for r in results if r.status == "fail"]
