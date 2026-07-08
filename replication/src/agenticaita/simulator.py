"""End-to-end functional replication harness for AGENTICAITA."""
from __future__ import annotations

import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Dict, Protocol

import pandas as pd

from .agents import AnalystConfig, RuleBasedAnalyst
from .azte import AdaptiveZScoreTriggerEngine, VolSample
from .cbd import CBDInputs, cbd_score
from .contracts import AnalystDecision, ExecutionRecord, RiskDecision
from .risk import DeterministicRiskManager, RiskConfig

class AnalystAgent(Protocol):
    def decide(self, event, cbd, episodic_memory: list[str] | None = None) -> AnalystDecision: ...
class RiskManagerAgent(Protocol):
    def evaluate(self, decision: AnalystDecision) -> RiskDecision: ...


@dataclass(frozen=True)
class SimulatorConfig:
    rolling_window: int = 30
    z_threshold: float = 2.0
    absolute_return_floor: float = 0.003
    global_cooldown_seconds: int = 1800
    per_asset_cooldown_seconds: int = 300
    benchmark_asset: str = "BTC"
    cbd_alpha: float = 0.5
    cbd_kappa: float = 0.5
    exit_horizon_minutes: int = 20
    transaction_cost_rate: float = 0.0


@dataclass(frozen=True)
class ExitResult:
    timestamp: pd.Timestamp
    price: float
    reason: str
    execution_model: str


class PipelineSimulator:
    """Runs AZTE -> Analyst -> Risk Manager -> Executor over OHLCV closes."""

    def __init__(self, config: SimulatorConfig | None = None, risk: RiskConfig | None = None, analyst: AnalystConfig | None = None, analyst_agent: AnalystAgent | None = None, risk_manager: RiskManagerAgent | None = None, episodic_memory_depth: int = 0) -> None:
        self.config = config or SimulatorConfig()
        self.azte = AdaptiveZScoreTriggerEngine(
            window=self.config.rolling_window,
            z_threshold=self.config.z_threshold,
            absolute_return_floor=self.config.absolute_return_floor,
        )
        self.analyst = analyst_agent or RuleBasedAnalyst(analyst)
        self.risk = risk_manager or DeterministicRiskManager(risk)
        self.episodic_memory_depth = max(0, int(episodic_memory_depth))
        self.price_windows: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=self.config.rolling_window))
        self.pipeline_log: list[dict] = []
        self.vol_history: list[dict] = []
        self.trades: list[dict] = []
        self._last_global_invocation: pd.Timestamp | None = None
        self._last_asset_invocation: Dict[str, pd.Timestamp] = {}
        self._prices_by_asset: dict[str, pd.DataFrame] = {}
        self.execution_model = "close_only_fixed_horizon"

    def _cooldown_block_reason(self, timestamp: pd.Timestamp, asset: str) -> str | None:
        if self._last_global_invocation is not None:
            elapsed = (timestamp - self._last_global_invocation).total_seconds()
            if elapsed < self.config.global_cooldown_seconds:
                return "pipeline_busy_or_global_cooldown"
        if asset in self._last_asset_invocation:
            elapsed = (timestamp - self._last_asset_invocation[asset]).total_seconds()
            if elapsed < self.config.per_asset_cooldown_seconds:
                return "per_asset_cooldown"
        return None

    def _future_rows(self, asset: str, timestamp: pd.Timestamp) -> pd.DataFrame:
        asset_df = self._prices_by_asset[asset]
        start = asset_df["timestamp"].searchsorted(timestamp, side="right")
        return asset_df.iloc[start : start + self.config.exit_horizon_minutes]

    def _close_only_exit(self, asset: str, timestamp: pd.Timestamp, fallback: float) -> ExitResult:
        future = self._future_rows(asset, timestamp)
        if future.empty:
            return ExitResult(timestamp, fallback, "no_future_close_only_fallback", "close_only_fixed_horizon")
        row = future.iloc[-1]
        return ExitResult(pd.Timestamp(row["timestamp"]), float(row["close"]), "fixed_horizon_close_only_fallback", "close_only_fixed_horizon")

    def _ohlcv_exit(self, asset: str, timestamp: pd.Timestamp, decision) -> ExitResult:
        future = self._future_rows(asset, timestamp)
        if future.empty:
            return ExitResult(timestamp, decision.entry_price, "no_future_ohlcv_fallback", "ohlcv_intrabar_stop_take_profit")

        for row in future.itertuples(index=False):
            row_timestamp = pd.Timestamp(row.timestamp)
            high = float(row.high)
            low = float(row.low)
            if decision.signal == "long":
                stop_hit = low <= decision.stop_loss
                take_profit_hit = high >= decision.take_profit
            else:
                stop_hit = high >= decision.stop_loss
                take_profit_hit = low <= decision.take_profit

            if stop_hit:
                reason = "stop_loss_intrabar_tie_breaker" if take_profit_hit else "stop_loss_intrabar"
                return ExitResult(row_timestamp, decision.stop_loss, reason, "ohlcv_intrabar_stop_take_profit")
            if take_profit_hit:
                return ExitResult(row_timestamp, decision.take_profit, "take_profit_intrabar", "ohlcv_intrabar_stop_take_profit")

        row = future.iloc[-1]
        return ExitResult(pd.Timestamp(row["timestamp"]), float(row["close"]), "fixed_horizon_ohlcv_timeout", "ohlcv_intrabar_stop_take_profit")

    def _exit_for_decision(self, timestamp: pd.Timestamp, decision) -> ExitResult:
        if {"high", "low"}.issubset(self._prices_by_asset[decision.asset].columns):
            return self._ohlcv_exit(decision.asset, timestamp, decision)
        return self._close_only_exit(decision.asset, timestamp, decision.entry_price)

    def _episodic_memory(self, asset: str) -> list[str]:
        rows = [str(r.get("analyst_reasoning", "")) for r in self.pipeline_log if r.get("asset") == asset and r.get("analyst_reasoning")]
        return rows[-self.episodic_memory_depth :] if self.episodic_memory_depth else []

    def _agent_warnings(self) -> str:
        return " | ".join(str(w) for a in (self.analyst, self.risk) if (w := getattr(a, "last_warning", "")))

    def _execute(self, timestamp: pd.Timestamp, decision, size_usd: float) -> ExecutionRecord:
        exit_result = self._exit_for_decision(timestamp, decision)
        direction = 1.0 if decision.signal == "long" else -1.0
        gross_return = direction * (exit_result.price - decision.entry_price) / decision.entry_price
        gross_pnl = size_usd * gross_return
        cost = size_usd * self.config.transaction_cost_rate
        return ExecutionRecord(
            timestamp=str(timestamp),
            exit_timestamp=str(exit_result.timestamp),
            asset=decision.asset,
            signal=decision.signal,
            entry_price=decision.entry_price,
            exit_price=exit_result.price,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            size_usd=size_usd,
            gross_pnl_usd=gross_pnl,
            net_pnl_usd=gross_pnl - cost,
            reason=exit_result.reason,
            execution_model=exit_result.execution_model,
            dry_run=True,
        )

    def run(self, ohlcv: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        df = ohlcv.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.sort_values(["timestamp", "asset"]).reset_index(drop=True)
        self.execution_model = "ohlcv_intrabar_stop_take_profit" if {"high", "low"}.issubset(df.columns) else "close_only_fixed_horizon"
        self._prices_by_asset = {asset: g.sort_values("timestamp").reset_index(drop=True) for asset, g in df.groupby("asset")}

        for row in df.itertuples(index=False):
            timestamp = pd.Timestamp(row.timestamp)
            asset = str(row.asset)
            price = float(row.close)
            self.price_windows[asset].append(price)
            sample, event = self.azte.update(str(timestamp), asset, price)
            self.vol_history.append(sample.__dict__)
            if event is None:
                continue

            blocked = self._cooldown_block_reason(timestamp, asset)
            if blocked:
                self.pipeline_log.append({
                    "timestamp": str(timestamp), "asset": asset, "event": "trigger_discarded", "reason": blocked,
                    "z_score": event.z_score, "analyst_signal": None, "risk_approved": None,
                })
                continue

            self._last_global_invocation = timestamp
            self._last_asset_invocation[asset] = timestamp
            benchmark_prices = list(self.price_windows[self.config.benchmark_asset])
            asset_prices = list(self.price_windows[asset])
            cbd = cbd_score(CBDInputs(event.z_score, asset_prices, benchmark_prices, self.config.cbd_alpha, self.config.cbd_kappa))
            analyst_decision = self.analyst.decide(event, cbd, self._episodic_memory(asset))
            risk_decision = self.risk.evaluate(analyst_decision)
            agent_warnings = self._agent_warnings()
            self.pipeline_log.append({
                "timestamp": str(timestamp),
                "asset": asset,
                "event": "trigger_admitted",
                "reason": event.reason,
                "z_score": event.z_score,
                "cbd_score": cbd.omega,
                "analyst_signal": analyst_decision.signal,
                "analyst_confidence": analyst_decision.confidence,
                "risk_approved": risk_decision.approved,
                "risk_rejection_reason": risk_decision.rejection_reason,
                "analyst_reasoning": analyst_decision.reasoning,
                "risk_summary": risk_decision.negotiation_summary,
                "agent_warnings": agent_warnings,
            })
            if risk_decision.approved:
                self.trades.append(self._execute(timestamp, analyst_decision, risk_decision.size_usd).to_dict())

        return pd.DataFrame(self.pipeline_log), pd.DataFrame(self.trades), pd.DataFrame(self.vol_history)


def write_sqlite(path: str | Path, pipeline_log: pd.DataFrame, trades: pd.DataFrame, vol_history: pd.DataFrame) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        pipeline_log.to_sql("pipeline_log", conn, if_exists="replace", index=False)
        trades.to_sql("trades", conn, if_exists="replace", index=False)
        vol_history.to_sql("vol_history", conn, if_exists="replace", index=False)
