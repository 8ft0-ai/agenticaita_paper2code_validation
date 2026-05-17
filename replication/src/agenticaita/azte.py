"""Adaptive Z-score Trigger Engine (AZTE).

This module implements the trigger equations reported in the AGENTICAITA
paper. It is deliberately deterministic and auditable: every observed return
can be serialised to a volatility-history table.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from math import isfinite
from typing import Deque, Dict, Optional

import numpy as np


@dataclass(frozen=True)
class VolSample:
    timestamp: str
    asset: str
    price: float
    prev_price: float | None
    signed_return: float | None
    abs_return: float | None
    rolling_mean: float | None
    rolling_std: float | None
    z_score: float | None
    triggered: bool
    reason: str


@dataclass(frozen=True)
class TriggerEvent:
    timestamp: str
    asset: str
    price: float
    signed_return: float
    abs_return: float
    rolling_mean: float
    rolling_std: float
    z_score: float
    reason: str


class AdaptiveZScoreTriggerEngine:
    """Stateful rolling anomaly detector.

    The paper defines r_t = |(p_t - p_{t-1}) / p_{t-1}| and triggers when
    z_t >= 2.0 or r_t >= 0.003. To avoid look-ahead bias, this implementation
    calculates z_t against the previous W return observations, then appends r_t.
    """

    def __init__(
        self,
        window: int = 30,
        z_threshold: float = 2.0,
        absolute_return_floor: float = 0.003,
    ) -> None:
        if window < 2:
            raise ValueError("window must be at least 2")
        self.window = int(window)
        self.z_threshold = float(z_threshold)
        self.absolute_return_floor = float(absolute_return_floor)
        self._returns: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=self.window))
        self._last_price: Dict[str, float] = {}

    def update(self, timestamp: str, asset: str, price: float) -> tuple[VolSample, Optional[TriggerEvent]]:
        if price <= 0 or not isfinite(price):
            raise ValueError(f"Invalid price for {asset}: {price}")

        prev_price = self._last_price.get(asset)
        self._last_price[asset] = float(price)
        if prev_price is None:
            sample = VolSample(timestamp, asset, price, None, None, None, None, None, None, False, "warmup_no_previous_price")
            return sample, None

        signed_return = (float(price) - prev_price) / prev_price
        abs_return = abs(signed_return)
        history = self._returns[asset]

        rolling_mean: float | None = None
        rolling_std: float | None = None
        z_score: float | None = None
        triggered = False
        reason = "warmup"

        if len(history) >= self.window:
            arr = np.asarray(history, dtype=float)
            rolling_mean = float(arr.mean())
            rolling_std = float(arr.std(ddof=1))
            if rolling_std > 0:
                z_score = (abs_return - rolling_mean) / rolling_std
            else:
                z_score = float("inf") if abs_return > rolling_mean else 0.0

            z_trigger = z_score >= self.z_threshold
            floor_trigger = abs_return >= self.absolute_return_floor
            triggered = bool(z_trigger or floor_trigger)
            if z_trigger and floor_trigger:
                reason = "z_score_and_abs_return_floor"
            elif z_trigger:
                reason = "z_score"
            elif floor_trigger:
                reason = "abs_return_floor"
            else:
                reason = "none"

        history.append(abs_return)
        sample = VolSample(
            timestamp=timestamp,
            asset=asset,
            price=float(price),
            prev_price=prev_price,
            signed_return=signed_return,
            abs_return=abs_return,
            rolling_mean=rolling_mean,
            rolling_std=rolling_std,
            z_score=z_score,
            triggered=triggered,
            reason=reason,
        )
        event = None
        if triggered and z_score is not None and rolling_mean is not None and rolling_std is not None:
            event = TriggerEvent(
                timestamp=timestamp,
                asset=asset,
                price=float(price),
                signed_return=signed_return,
                abs_return=abs_return,
                rolling_mean=rolling_mean,
                rolling_std=rolling_std,
                z_score=z_score,
                reason=reason,
            )
        return sample, event
