"""Experiment summaries and statistical checks."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Iterable

import pandas as pd
from scipy.stats import binomtest, norm


@dataclass(frozen=True)
class Summary:
    total_invocations: int
    analyst_long: int
    analyst_short: int
    analyst_wait: int
    analyst_provenance_counts: dict[str, int]
    analyst_signal_by_provenance: dict[str, dict[str, int]]
    analyst_contract_error_counts: dict[str, int]
    analyst_repair_attempted: int
    risk_approved: int
    risk_rejected: int
    risk_not_evaluated: int
    risk_provenance_counts: dict[str, int]
    risk_contract_error_counts: dict[str, int]
    risk_repair_attempted: int
    risk_rejection_reasons: dict[str, int]
    approvals_by_analyst_provenance: dict[str, int]
    approvals_by_risk_provenance: dict[str, int]
    stage_accounting_valid: bool
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


def _value_counts(frame: pd.DataFrame, column: str, *, default: str | None = None) -> dict[str, int]:
    if frame.empty or column not in frame:
        return {}
    counter: Counter[str] = Counter()
    for raw in frame[column].fillna("").astype(str):
        value = raw.strip() or default
        if value:
            counter[value] += 1
    return dict(sorted(counter.items()))


def _error_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame:
        return {}
    counter: Counter[str] = Counter()
    for raw in frame[column].fillna("").astype(str):
        value = raw.strip()
        if value:
            # Keep diagnostics useful but bounded across provider-specific wording.
            category = value.split(";", 1)[0][:160]
            counter[category] += 1
    return dict(sorted(counter.items()))


def _signal_by_provenance(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    if frame.empty or "analyst_signal" not in frame:
        return {}
    result: dict[str, Counter[str]] = {}
    for row in frame.itertuples(index=False):
        provenance = str(getattr(row, "analyst_provenance", "") or "legacy_or_deterministic")
        signal = str(getattr(row, "analyst_signal", "") or "unknown")
        result.setdefault(provenance, Counter())[signal] += 1
    return {key: dict(sorted(counter.items())) for key, counter in sorted(result.items())}


def _approval_counts(frame: pd.DataFrame, provenance_column: str) -> dict[str, int]:
    if frame.empty or "risk_approved" not in frame or provenance_column not in frame:
        return {}
    approved = frame[frame["risk_approved"] == True]  # noqa: E712
    return _value_counts(approved, provenance_column, default="legacy_or_deterministic")


def summarise(pipeline_log: pd.DataFrame, trades: pd.DataFrame) -> Summary:
    if pipeline_log.empty or "event" not in pipeline_log:
        admitted = pd.DataFrame()
    else:
        admitted = pipeline_log[pipeline_log["event"] == "trigger_admitted"].copy()

    total_invocations = int(len(admitted))
    analyst_long = int((admitted["analyst_signal"] == "long").sum()) if "analyst_signal" in admitted else 0
    analyst_short = int((admitted["analyst_signal"] == "short").sum()) if "analyst_signal" in admitted else 0
    analyst_wait = int((admitted["analyst_signal"] == "wait").sum()) if "analyst_signal" in admitted else 0
    directional_count = analyst_long + analyst_short

    if admitted.empty:
        risk_rows = admitted
    elif "risk_evaluated" in admitted:
        risk_rows = admitted[admitted["risk_evaluated"] == True]  # noqa: E712
    elif "analyst_signal" in admitted:
        risk_rows = admitted[admitted["analyst_signal"].isin(["long", "short"])]
    else:
        risk_rows = admitted.iloc[0:0]

    risk_approved = int((risk_rows["risk_approved"] == True).sum()) if "risk_approved" in risk_rows else 0  # noqa: E712
    risk_rejected = int((risk_rows["risk_approved"] == False).sum()) if "risk_approved" in risk_rows else 0  # noqa: E712
    risk_not_evaluated = max(0, total_invocations - int(len(risk_rows)))

    rejection_reasons: Counter[str] = Counter()
    if "risk_rejection_reason" in risk_rows:
        rejected = risk_rows[risk_rows["risk_approved"] == False] if "risk_approved" in risk_rows else risk_rows.iloc[0:0]  # noqa: E712
        for value in rejected["risk_rejection_reason"].fillna("").astype(str):
            reason = value.strip() or "unspecified"
            rejection_reasons[reason] += 1

    analyst_provenance_counts = _value_counts(admitted, "analyst_provenance", default="legacy_or_deterministic")
    analyst_signal_by_provenance = _signal_by_provenance(admitted)
    analyst_contract_error_counts = _error_counts(admitted, "analyst_contract_error")
    analyst_repair_attempted = int(admitted["analyst_repair_attempted"].fillna(False).astype(bool).sum()) if "analyst_repair_attempted" in admitted else 0
    risk_provenance_counts = _value_counts(admitted, "risk_provenance", default="legacy_or_deterministic")
    risk_contract_error_counts = _error_counts(admitted, "risk_contract_error")
    risk_repair_attempted = int(admitted["risk_repair_attempted"].fillna(False).astype(bool).sum()) if "risk_repair_attempted" in admitted else 0

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
    stage_accounting_valid = (
        analyst_long + analyst_short + analyst_wait == total_invocations
        and risk_approved + risk_rejected <= directional_count
        and (friction is None or friction <= 100.0)
    )
    exact_p = binomtest(wins, n, 0.5, alternative="greater").pvalue if n else None
    z = (wins - n * 0.5) / ((n * 0.5 * 0.5) ** 0.5) if n else None
    normal_p = 1.0 - norm.cdf(z) if z is not None else None

    return Summary(
        total_invocations=total_invocations,
        analyst_long=analyst_long,
        analyst_short=analyst_short,
        analyst_wait=analyst_wait,
        analyst_provenance_counts=analyst_provenance_counts,
        analyst_signal_by_provenance=analyst_signal_by_provenance,
        analyst_contract_error_counts=analyst_contract_error_counts,
        analyst_repair_attempted=analyst_repair_attempted,
        risk_approved=risk_approved,
        risk_rejected=risk_rejected,
        risk_not_evaluated=risk_not_evaluated,
        risk_provenance_counts=risk_provenance_counts,
        risk_contract_error_counts=risk_contract_error_counts,
        risk_repair_attempted=risk_repair_attempted,
        risk_rejection_reasons=dict(sorted(rejection_reasons.items())),
        approvals_by_analyst_provenance=_approval_counts(admitted, "analyst_provenance"),
        approvals_by_risk_provenance=_approval_counts(admitted, "risk_provenance"),
        stage_accounting_valid=stage_accounting_valid,
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
