"""Experiment summaries and statistical checks."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable

import pandas as pd
from scipy.stats import binomtest, norm


@dataclass(frozen=True)
class Summary:
    total_invocations: int
    analyst_long: int
    analyst_short: int
    analyst_wait: int
    risk_approved: int
    risk_rejected: int
    trades_executed: int
    wins: int
    losses: int
    net_pnl_usd: float
    gross_profit_usd: float
    gross_loss_usd_abs: float
    win_rate_pct: float | None
    profit_factor: float | None
    agentic_friction_pct: float | None
    exact_binomial_p_one_sided: float | None
    normal_approx_p_one_sided: float | None

    def to_dict(self) -> dict:
        return asdict(self)


def summarise(pipeline_log: pd.DataFrame, trades: pd.DataFrame) -> Summary:
    total_invocations = int((pipeline_log["event"] == "trigger_admitted").sum()) if not pipeline_log.empty else 0
    analyst_long = int((pipeline_log["analyst_signal"] == "long").sum()) if "analyst_signal" in pipeline_log else 0
    analyst_short = int((pipeline_log["analyst_signal"] == "short").sum()) if "analyst_signal" in pipeline_log else 0
    analyst_wait = int((pipeline_log["analyst_signal"] == "wait").sum()) if "analyst_signal" in pipeline_log else 0
    risk_approved = int((pipeline_log["risk_approved"] == True).sum()) if "risk_approved" in pipeline_log else 0  # noqa: E712
    risk_rejected = int((pipeline_log["risk_approved"] == False).sum()) if "risk_approved" in pipeline_log else 0  # noqa: E712

    if trades.empty:
        wins = losses = 0
        net = gross_profit = gross_loss = 0.0
    else:
        wins = int((trades["net_pnl_usd"] > 0).sum())
        losses = int((trades["net_pnl_usd"] <= 0).sum())
        net = float(trades["net_pnl_usd"].sum())
        gross_profit = float(trades.loc[trades["net_pnl_usd"] > 0, "net_pnl_usd"].sum())
        gross_loss = abs(float(trades.loc[trades["net_pnl_usd"] <= 0, "net_pnl_usd"].sum()))

    n = wins + losses
    win_rate = 100.0 * wins / n if n else None
    profit_factor = gross_profit / gross_loss if gross_loss else None
    friction = 100.0 * (analyst_wait + risk_rejected) / total_invocations if total_invocations else None
    exact_p = binomtest(wins, n, 0.5, alternative="greater").pvalue if n else None
    z = (wins - n * 0.5) / ((n * 0.5 * 0.5) ** 0.5) if n else None
    normal_p = 1.0 - norm.cdf(z) if z is not None else None

    return Summary(
        total_invocations=total_invocations,
        analyst_long=analyst_long,
        analyst_short=analyst_short,
        analyst_wait=analyst_wait,
        risk_approved=risk_approved,
        risk_rejected=risk_rejected,
        trades_executed=len(trades),
        wins=wins,
        losses=losses,
        net_pnl_usd=net,
        gross_profit_usd=gross_profit,
        gross_loss_usd_abs=gross_loss,
        win_rate_pct=win_rate,
        profit_factor=profit_factor,
        agentic_friction_pct=friction,
        exact_binomial_p_one_sided=exact_p,
        normal_approx_p_one_sided=normal_p,
    )


def transaction_cost_sensitivity(net_pnl_usd: float, total_notional_usd: float, rates: dict[str, float]) -> list[dict]:
    rows = []
    for name, rate in rates.items():
        cost = total_notional_usd * float(rate)
        rows.append({
            "scenario": name,
            "round_trip_rate": float(rate),
            "total_cost_usd": cost,
            "adjusted_net_pnl_usd": net_pnl_usd - cost,
        })
    return rows
