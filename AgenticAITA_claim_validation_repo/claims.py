"""Reported quantities from the AGENTICAITA paper.

The values are copied from the paper tables and prose.  This module is
intentionally data-only so that the calculation code in ``metrics.py`` can be
reviewed separately.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineCounts:
    total_invocations: int = 157
    analyst_long: int = 142
    analyst_short: int = 2
    analyst_wait: int = 13
    risk_manager_approved: int = 139
    risk_manager_rejected: int = 5
    trades_executed: int = 139
    unique_assets: int = 76

    @property
    def reaching_risk_manager(self) -> int:
        return self.total_invocations - self.analyst_wait


@dataclass(frozen=True)
class TradingMetrics:
    total_trades: int = 139
    wins: int = 72
    losses: int = 67
    gross_profit_usd: float = 79.67
    gross_loss_usd_abs: float = 94.74
    net_pnl_usd: float = -15.07
    total_notional_usd: float = 26079.0
    btc_buy_hold_pnl_usd: float = -3912.0
    reported_alpha_usd: float = 3896.0
    mean_stop_loss_pct: float = 0.627
    mean_take_profit_pct: float = 1.894


@dataclass(frozen=True)
class ReportedCostScenario:
    name: str
    round_trip_rate: float
    reported_total_cost_usd: float
    reported_adjusted_net_pnl_usd: float


COST_SCENARIOS: tuple[ReportedCostScenario, ...] = (
    ReportedCostScenario("Zero cost", 0.0, 0.0, -15.07),
    ReportedCostScenario("Conservative maker only", 0.0004, 10.43, -25.50),
    ReportedCostScenario("Realistic taker plus spread", 0.0010, 26.09, -41.16),
    ReportedCostScenario("Adverse illiquid long tail", 0.0020, 52.18, -67.25),
)


@dataclass(frozen=True)
class AssetClassRow:
    name: str
    trades: int
    win_rate_pct: float
    avg_confidence: float
    net_pnl_usd: float


ASSET_CLASS_ROWS: tuple[AssetClassRow, ...] = (
    AssetClassRow("Large caps", 15, 60.0, 0.757, 3.06),
    AssetClassRow("Mid caps", 55, 52.7, 0.755, -9.78),
    AssetClassRow("Long tail", 69, 49.3, 0.753, -8.36),
)
