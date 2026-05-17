"""Typed contracts for the deliberative pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Signal = Literal["long", "short", "wait"]


@dataclass(frozen=True)
class AnalystDecision:
    asset: str
    signal: Signal
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    size_usd: float
    cbd_score: float
    z_score: float
    reasoning: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    size_usd: float
    rejection_reason: str
    negotiation_summary: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ExecutionRecord:
    timestamp: str
    exit_timestamp: str
    asset: str
    signal: Signal
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    size_usd: float
    gross_pnl_usd: float
    net_pnl_usd: float
    reason: str
    execution_model: str
    dry_run: bool = True

    def to_dict(self) -> dict:
        return asdict(self)
