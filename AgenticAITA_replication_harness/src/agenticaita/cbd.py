"""Correlation-Break Diversification (CBD) utilities."""
from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class CBDInputs:
    z_score: float
    asset_prices: Sequence[float]
    benchmark_prices: Sequence[float]
    alpha: float = 0.5
    kappa: float = 0.5


@dataclass(frozen=True)
class CBDResult:
    z_tilde: float
    rho: float
    correlation_break: float
    omega: float


def z_tilde(z_score: float, threshold: float = 2.0, kappa: float = 0.5) -> float:
    """Saturated anomaly score from the paper's Eq. 10."""
    magnitude = abs(float(z_score))
    if magnitude < threshold:
        return 0.0
    return 1.0 - exp(-float(kappa) * (magnitude - threshold))


def safe_correlation(x: Sequence[float], y: Sequence[float]) -> float:
    """Return Pearson correlation, falling back to 0 for degenerate inputs."""
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    n = min(len(x_arr), len(y_arr))
    if n < 3:
        return 0.0
    x_arr = x_arr[-n:]
    y_arr = y_arr[-n:]
    if not (np.all(np.isfinite(x_arr)) and np.all(np.isfinite(y_arr))):
        return 0.0
    if np.std(x_arr) == 0 or np.std(y_arr) == 0:
        return 0.0
    rho = float(np.corrcoef(x_arr, y_arr)[0, 1])
    return rho if isfinite(rho) else 0.0


def cbd_score(inputs: CBDInputs) -> CBDResult:
    if not 0.0 <= inputs.alpha <= 1.0:
        raise ValueError("alpha must be in [0, 1]")
    z_norm = z_tilde(inputs.z_score, kappa=inputs.kappa)
    rho = safe_correlation(inputs.asset_prices, inputs.benchmark_prices)
    correlation_break = 1.0 - abs(rho)
    omega = inputs.alpha * z_norm + (1.0 - inputs.alpha) * correlation_break
    return CBDResult(z_tilde=z_norm, rho=rho, correlation_break=correlation_break, omega=omega)
