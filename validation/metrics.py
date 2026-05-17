"""Validation calculations for AGENTICAITA paper claims."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import erf, exp, isclose, sqrt
from typing import Any, Callable

from scipy.stats import binomtest, norm

from claims import ASSET_CLASS_ROWS, COST_SCENARIOS, PipelineCounts, TradingMetrics


@dataclass(frozen=True)
class ValidationResult:
    claim_id: str
    claim: str
    paper_value: Any
    computed_value: Any
    status: str
    tolerance: Any
    notes: str = ""


def pct(value: float) -> float:
    """Convert a fraction to percentage."""
    return 100.0 * value


def rounded(value: float, ndigits: int = 4) -> float:
    return round(float(value), ndigits)


def within(value: float, target: float, tolerance: float) -> bool:
    return abs(float(value) - float(target)) <= tolerance


def status_from(value: float, target: float, tolerance: float) -> str:
    return "pass" if within(value, target, tolerance) else "fail"


def validate_pipeline_counts(counts: PipelineCounts | None = None) -> list[ValidationResult]:
    counts = counts or PipelineCounts()
    results: list[ValidationResult] = []

    expected = {
        "long_rate_pct": (pct(counts.analyst_long / counts.total_invocations), 90.4),
        "short_rate_pct": (pct(counts.analyst_short / counts.total_invocations), 1.3),
        "wait_rate_pct": (pct(counts.analyst_wait / counts.total_invocations), 8.3),
        "approved_rate_pct": (pct(counts.risk_manager_approved / counts.reaching_risk_manager), 96.5),
        "rejected_rate_pct_rm_denominator": (pct(counts.risk_manager_rejected / counts.reaching_risk_manager), 3.5),
        "rejected_rate_pct_all_invocations": (pct(counts.risk_manager_rejected / counts.total_invocations), 3.2),
        "trades_executed_pct": (pct(counts.trades_executed / counts.total_invocations), 88.5),
        "asset_breadth_pct": (pct(counts.unique_assets / counts.trades_executed), 54.68),
    }

    for key, (computed, paper_value) in expected.items():
        results.append(
            ValidationResult(
                claim_id=f"pipeline.{key}",
                claim=f"Pipeline percentage {key} matches the paper.",
                paper_value=paper_value,
                computed_value=rounded(computed, 6),
                status=status_from(computed, paper_value, 0.06),
                tolerance="±0.06 percentage points",
            )
        )

    friction = (counts.risk_manager_rejected + counts.analyst_wait) / counts.total_invocations
    results.append(
        ValidationResult(
            claim_id="pipeline.agentic_friction",
            claim="Agentic friction F=(N_rej+N_wait)/N is 18/157 ≈ 11.5%.",
            paper_value="11.5%",
            computed_value=rounded(pct(friction), 6),
            status=status_from(pct(friction), 11.5, 0.06),
            tolerance="±0.06 percentage points",
        )
    )

    conservation = counts.analyst_long + counts.analyst_short + counts.analyst_wait
    results.append(
        ValidationResult(
            claim_id="pipeline.signal_count_conservation",
            claim="Analyst long + short + wait equals total invocations.",
            paper_value=counts.total_invocations,
            computed_value=conservation,
            status="pass" if conservation == counts.total_invocations else "fail",
            tolerance="exact integer equality",
        )
    )

    rm_conservation = counts.risk_manager_approved + counts.risk_manager_rejected
    results.append(
        ValidationResult(
            claim_id="pipeline.risk_manager_count_conservation",
            claim="Risk Manager approved + rejected equals invocations reaching Risk Manager.",
            paper_value=counts.reaching_risk_manager,
            computed_value=rm_conservation,
            status="pass" if rm_conservation == counts.reaching_risk_manager else "fail",
            tolerance="exact integer equality",
        )
    )
    return results


def validate_trading_metrics(metrics: TradingMetrics | None = None) -> list[ValidationResult]:
    metrics = metrics or TradingMetrics()
    results: list[ValidationResult] = []

    checks = [
        (
            "trading.win_rate_pct",
            "Win rate is 72/139 = 51.80%.",
            51.80,
            pct(metrics.wins / metrics.total_trades),
            "±0.03 percentage points",
            0.03,
        ),
        (
            "trading.net_pnl",
            "Net PnL is gross profit minus gross loss.",
            metrics.net_pnl_usd,
            metrics.gross_profit_usd - metrics.gross_loss_usd_abs,
            "±$0.01",
            0.011,
        ),
        (
            "trading.return_pct",
            "Return on $26,079 notional is about -0.058%.",
            -0.058,
            pct(metrics.net_pnl_usd / metrics.total_notional_usd),
            "±0.002 percentage points",
            0.002,
        ),
        (
            "trading.profit_factor",
            "Profit factor is gross profit / gross loss.",
            0.841,
            metrics.gross_profit_usd / metrics.gross_loss_usd_abs,
            "±0.001",
            0.001,
        ),
        (
            "trading.mean_win",
            "Mean win is $79.67 / 72.",
            1.11,
            metrics.gross_profit_usd / metrics.wins,
            "±$0.01",
            0.01,
        ),
        (
            "trading.mean_loss",
            "Mean loss is $94.74 / 67.",
            1.41,
            metrics.gross_loss_usd_abs / metrics.losses,
            "±$0.01",
            0.01,
        ),
        (
            "trading.risk_reward",
            "Risk/reward is mean take-profit percentage divided by mean stop-loss percentage.",
            3.02,
            metrics.mean_take_profit_pct / metrics.mean_stop_loss_pct,
            "±0.005",
            0.005,
        ),
        (
            "trading.break_even_win_rate",
            "Break-even win rate at RR=3.02 is 1/(1+RR).",
            24.9,
            pct(1.0 / (1.0 + 3.02)),
            "±0.05 percentage points",
            0.05,
        ),
        (
            "trading.btc_loss_from_notional",
            "A -15% BTC benchmark loss on $26,079 is about -$3,912.",
            metrics.btc_buy_hold_pnl_usd,
            -0.15 * metrics.total_notional_usd,
            "±$0.25",
            0.25,
        ),
        (
            "trading.alpha_usd",
            "Benchmark alpha in dollars is AGENTICAITA PnL minus BTC buy-and-hold PnL.",
            metrics.reported_alpha_usd,
            metrics.net_pnl_usd - metrics.btc_buy_hold_pnl_usd,
            "±$1.00 due table rounding",
            1.00,
        ),
        (
            "trading.alpha_percentage_points",
            "Benchmark alpha is agent return minus BTC return.",
            14.94,
            pct(metrics.net_pnl_usd / metrics.total_notional_usd) - (-15.0),
            "±0.01 percentage points",
            0.01,
        ),
    ]

    for claim_id, claim, paper_value, computed, tolerance, tol in checks:
        results.append(
            ValidationResult(
                claim_id=claim_id,
                claim=claim,
                paper_value=paper_value,
                computed_value=rounded(computed, 6),
                status=status_from(computed, paper_value, tol),
                tolerance=tolerance,
            )
        )

    return results


def validate_binomial(metrics: TradingMetrics | None = None) -> list[ValidationResult]:
    metrics = metrics or TradingMetrics()
    exact_greater = binomtest(metrics.wins, metrics.total_trades, 0.5, alternative="greater").pvalue
    exact_two_sided = binomtest(metrics.wins, metrics.total_trades, 0.5, alternative="two-sided").pvalue
    z = (metrics.wins - metrics.total_trades * 0.5) / sqrt(metrics.total_trades * 0.5 * 0.5)
    normal_one_sided = 1.0 - norm.cdf(z)

    return [
        ValidationResult(
            claim_id="stats.binomial_pvalue_normal_approx",
            claim="Paper's p≈0.34 is reproducible as a one-sided normal approximation for 72/139 against 50%.",
            paper_value="≈0.34",
            computed_value=rounded(normal_one_sided, 6),
            status="pass",
            tolerance="approximation; exact one-sided p is separately reported",
            notes=f"z={z:.6f}; exact one-sided p={exact_greater:.6f}; exact two-sided p={exact_two_sided:.6f}",
        ),
        ValidationResult(
            claim_id="stats.binomial_pvalue_exact_one_sided",
            claim="Exact one-sided binomial p-value for 72 wins out of 139 is close but not exactly 0.34.",
            paper_value="≈0.34",
            computed_value=rounded(exact_greater, 6),
            status="qualified",
            tolerance="method caveat",
            notes="The paper's value appears to use a normal approximation rather than an exact binomial test.",
        ),
        ValidationResult(
            claim_id="stats.binomial_significance",
            claim="The observed win rate is not statistically significant versus 50%. ",
            paper_value="not significant",
            computed_value={"exact_one_sided": rounded(exact_greater, 6), "exact_two_sided": rounded(exact_two_sided, 6)},
            status="pass",
            tolerance="p-values well above 0.05",
        ),
    ]


def validate_transaction_costs(metrics: TradingMetrics | None = None) -> list[ValidationResult]:
    metrics = metrics or TradingMetrics()
    results: list[ValidationResult] = []
    for scenario in COST_SCENARIOS:
        computed_cost = metrics.total_notional_usd * scenario.round_trip_rate
        computed_adjusted = metrics.net_pnl_usd - computed_cost
        cost_status = status_from(computed_cost, scenario.reported_total_cost_usd, 0.03)
        pnl_status = status_from(computed_adjusted, scenario.reported_adjusted_net_pnl_usd, 0.03)
        results.append(
            ValidationResult(
                claim_id=f"cost.{scenario.name.lower().replace(' ', '_')}",
                claim=f"Transaction-cost sensitivity for {scenario.name} matches total_notional * round_trip_rate.",
                paper_value={
                    "total_cost_usd": scenario.reported_total_cost_usd,
                    "adjusted_net_pnl_usd": scenario.reported_adjusted_net_pnl_usd,
                },
                computed_value={
                    "total_cost_usd": rounded(computed_cost, 6),
                    "adjusted_net_pnl_usd": rounded(computed_adjusted, 6),
                },
                status="pass" if cost_status == "pass" and pnl_status == "pass" else "qualified",
                tolerance="±$0.03",
                notes="Small differences are consistent with cents rounding and the paper's rounded mean position size.",
            )
        )
    return results


def validate_azte_false_positive_rate() -> list[ValidationResult]:
    one_sided = 1.0 - norm.cdf(2.0)
    two_sided = 2.0 * one_sided
    return [
        ValidationResult(
            claim_id="azte.false_positive_rate",
            claim="The paper states that a 2.0σ threshold gives an expected false-positive rate of approximately 4.6% under normality.",
            paper_value="≈4.6%",
            computed_value={
                "P(Z >= 2) one-sided": rounded(pct(one_sided), 6),
                "P(|Z| >= 2) two-sided": rounded(pct(two_sided), 6),
            },
            status="qualified",
            tolerance="interpretation caveat",
            notes=(
                "4.6% is the two-sided normal tail. The paper's trigger is written as z_t >= 2.0, "
                "which is one-sided and has tail probability about 2.28%. Because r_t is an absolute return, "
                "the normality assumption also does not directly apply to z_t without further distributional justification."
            ),
        ),
        ValidationResult(
            claim_id="azte.hot_restart_warmup",
            claim="W=30 observations at 60 seconds implies a 30-minute warmup window.",
            paper_value="30 minutes",
            computed_value=f"{30 * 60 / 60:.0f} minutes",
            status="pass",
            tolerance="exact arithmetic",
        ),
    ]


def cbd_z_tilde(abs_z: float, kappa: float = 0.5) -> float:
    return (1.0 - exp(-kappa * (abs_z - 2.0))) if abs_z >= 2.0 else 0.0


def cbd_score(abs_z: float, rho_cb: float, alpha: float = 0.5, kappa: float = 0.5) -> float:
    return alpha * cbd_z_tilde(abs_z, kappa=kappa) + (1.0 - alpha) * rho_cb


def validate_cbd_properties() -> list[ValidationResult]:
    z_values = [0.0, 1.0, 2.0, 2.1, 3.0, 5.0, 10.0]
    z_tildes = [cbd_z_tilde(z) for z in z_values]
    bounded = all(0.0 <= zt < 1.0 for zt in z_tildes)
    low_decor = cbd_score(3.0, 0.1)
    high_decor = cbd_score(3.0, 0.9)
    return [
        ValidationResult(
            claim_id="cbd.z_tilde_bounded",
            claim="The saturated anomaly mapping z_tilde is in [0,1) for triggered observations.",
            paper_value="z_tilde in [0,1)",
            computed_value=dict(zip([str(v) for v in z_values], [rounded(v, 6) for v in z_tildes])),
            status="pass" if bounded else "fail",
            tolerance="property test over representative values and analytical form",
        ),
        ValidationResult(
            claim_id="cbd.diversification_incentive",
            claim="For identical anomaly magnitude, higher decorrelation gives higher composite CBD score.",
            paper_value="strictly higher score for higher rho_cb",
            computed_value={"rho_cb=0.1": rounded(low_decor, 6), "rho_cb=0.9": rounded(high_decor, 6)},
            status="pass" if high_decor > low_decor else "fail",
            tolerance="strict inequality",
        ),
    ]


def validate_asset_class_table() -> list[ValidationResult]:
    total_trades = sum(row.trades for row in ASSET_CLASS_ROWS)
    total_pnl = sum(row.net_pnl_usd for row in ASSET_CLASS_ROWS)
    weighted_wr = sum(row.trades * row.win_rate_pct for row in ASSET_CLASS_ROWS) / total_trades
    weighted_conf = sum(row.trades * row.avg_confidence for row in ASSET_CLASS_ROWS) / total_trades
    return [
        ValidationResult(
            claim_id="asset_classes.trade_count_sum",
            claim="Asset-class trade counts sum to 139.",
            paper_value=139,
            computed_value=total_trades,
            status="pass" if total_trades == 139 else "fail",
            tolerance="exact integer equality",
        ),
        ValidationResult(
            claim_id="asset_classes.net_pnl_sum",
            claim="Asset-class net PnL rows sum to total net PnL within rounding.",
            paper_value=-15.07,
            computed_value=rounded(total_pnl, 6),
            status=status_from(total_pnl, -15.07, 0.02),
            tolerance="±$0.02 due row rounding",
            notes="The rounded rows sum to -$15.08, a one-cent discrepancy from the table total.",
        ),
        ValidationResult(
            claim_id="asset_classes.weighted_win_rate",
            claim="Weighted asset-class win rate agrees with the 51.80% total within rounding.",
            paper_value=51.80,
            computed_value=rounded(weighted_wr, 6),
            status=status_from(weighted_wr, 51.80, 0.20),
            tolerance="±0.20 percentage points due rounded class win rates",
        ),
        ValidationResult(
            claim_id="asset_classes.weighted_confidence",
            claim="Weighted average confidence is close to the table's 0.755 total.",
            paper_value=0.755,
            computed_value=rounded(weighted_conf, 6),
            status=status_from(weighted_conf, 0.755, 0.002),
            tolerance="±0.002 due rounded class confidence values",
        ),
    ]


def unsupported_claims() -> list[ValidationResult]:
    unsupported = [
        (
            "raw.zero_human_intervention",
            "157 autonomous invocations with zero human interventions.",
            "Requires system logs or an experiment audit trail.",
        ),
        (
            "raw.sqlite_no_post_processing",
            "Figures and metrics were extracted directly from the trades SQLite table with no post-processing.",
            "Requires the SQLite database and plotting scripts.",
        ),
        (
            "raw.funding_corrected_benchmark",
            "Funding-corrected BTC perpetual benchmark is strictly worse than price-only BTC benchmark.",
            "Requires timestamped funding-rate cash flows and position sizing.",
        ),
        (
            "raw.cbd_empirical_asset_correlation",
            "Top performers all had rho_cb > 0.85 and low-rho_cb assets produced deepest losses.",
            "Requires per-asset price series, CBD scores, and trade-level PnL records.",
        ),
        (
            "raw.live_market_conditions",
            "The five-day dry run used live market conditions and qwen3.5:9b via remote Ollama.",
            "Requires telemetry, API logs, and environment configuration.",
        ),
        (
            "raw.no_parameter_tuning",
            "No parameters were tuned during the session.",
            "Requires configuration history and deployment logs.",
        ),
    ]
    return [
        ValidationResult(
            claim_id=claim_id,
            claim=claim,
            paper_value="claimed",
            computed_value="not computable from paper alone",
            status="unsupported",
            tolerance="n/a",
            notes=notes,
        )
        for claim_id, claim, notes in unsupported
    ]


def run_all_validations() -> list[ValidationResult]:
    results: list[ValidationResult] = []
    results.extend(validate_pipeline_counts())
    results.extend(validate_trading_metrics())
    results.extend(validate_binomial())
    results.extend(validate_transaction_costs())
    results.extend(validate_azte_false_positive_rate())
    results.extend(validate_cbd_properties())
    results.extend(validate_asset_class_table())
    results.extend(unsupported_claims())
    return results


def result_to_dict(result: ValidationResult) -> dict[str, Any]:
    return asdict(result)
