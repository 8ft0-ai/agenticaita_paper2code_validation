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


def funding_accounting(ohlcv: pd.DataFrame, trades: pd.DataFrame) -> dict:
    price_only_net = float(trades["net_pnl_usd"].sum()) if not trades.empty else 0.0
    price_only = {
        "mode": "price_only",
        "status": "available",
        "net_pnl_usd": price_only_net,
        "description": "Trade PnL from price moves only; funding is excluded.",
    }
    if "funding_rate" not in ohlcv.columns:
        return {
            "price_only": price_only,
            "funding_aware": {
                "mode": "funding_aware",
                "status": "unsupported",
                "reason": "input data has no funding_rate column",
                "missing_funding_assets": sorted(str(asset) for asset in trades["asset"].dropna().unique()) if "asset" in trades else [],
            },
        }

    funding = ohlcv[["timestamp", "asset", "funding_rate"]].copy()
    funding["timestamp"] = pd.to_datetime(funding["timestamp"], utc=True)
    funding = funding.dropna(subset=["funding_rate"])
    funding_counts = {str(asset): int(count) for asset, count in funding.groupby("asset").size().sort_index().items()}
    if trades.empty:
        status = "available" if not funding.empty else "unsupported"
        return {
            "price_only": price_only,
            "funding_aware": {
                "mode": "funding_aware",
                "status": status,
                "funding_rows_by_asset": funding_counts,
                "net_funding_pnl_usd": 0.0,
                "funding_adjusted_net_pnl_usd": price_only_net,
                "missing_funding_assets": [],
            },
        }
    if funding.empty:
        return {
            "price_only": price_only,
            "funding_aware": {
                "mode": "funding_aware",
                "status": "unsupported",
                "reason": "funding_rate column is present but contains no funding rows",
                "funding_rows_by_asset": funding_counts,
                "missing_funding_assets": sorted(str(asset) for asset in trades["asset"].dropna().unique()),
            },
        }

    net_funding_pnl = 0.0
    unsupported_trades = 0
    missing_assets: set[str] = set()
    for trade in trades.itertuples(index=False):
        asset = str(trade.asset)
        asset_funding = funding[funding["asset"] == asset]
        if asset_funding.empty:
            unsupported_trades += 1
            missing_assets.add(asset)
            continue
        entry_timestamp = pd.Timestamp(trade.timestamp)
        exit_timestamp = pd.Timestamp(trade.exit_timestamp)
        in_window = asset_funding[(asset_funding["timestamp"] > entry_timestamp) & (asset_funding["timestamp"] <= exit_timestamp)]
        funding_rate_sum = float(in_window["funding_rate"].sum())
        direction = 1.0 if trade.signal == "long" else -1.0
        net_funding_pnl += -direction * float(trade.size_usd) * funding_rate_sum

    status = "available" if unsupported_trades == 0 else "qualified"
    return {
        "price_only": price_only,
        "funding_aware": {
            "mode": "funding_aware",
            "status": status,
            "reason": None if status == "available" else "one or more traded assets have no funding rows",
            "funding_rows_by_asset": funding_counts,
            "missing_funding_assets": sorted(missing_assets),
            "unsupported_trade_count": unsupported_trades,
            "net_funding_pnl_usd": net_funding_pnl,
            "funding_adjusted_net_pnl_usd": price_only_net + net_funding_pnl,
        },
    }
