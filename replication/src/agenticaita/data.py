"""Data loading and deterministic synthetic market generator."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

OHLCV_COLUMNS = ("open", "high", "low", "close", "volume")


def load_ohlcv_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"timestamp", "asset", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {sorted(missing)}")
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    for column in OHLCV_COLUMNS:
        if column in df.columns:
            df[column] = df[column].astype(float)
    return df.sort_values(["timestamp", "asset"]).reset_index(drop=True)


def generate_synthetic_ohlcv(
    assets: Iterable[str],
    minutes: int = 1440,
    seed: int = 42,
    macro_shock_minute: int = 720,
    macro_shock_size: float = -0.08,
) -> pd.DataFrame:
    """Generate correlated minute closes with a BTC correction and idiosyncratic shocks."""
    rng = np.random.default_rng(seed)
    assets = list(assets)
    timestamps = pd.date_range("2026-04-06", periods=minutes, freq="min", tz="UTC")
    btc_noise = rng.normal(0, 0.0007, size=minutes)
    btc_noise[macro_shock_minute : macro_shock_minute + 20] += macro_shock_size / 20.0
    btc_prices = 70000 * np.exp(np.cumsum(btc_noise))

    rows: list[dict] = []
    for asset in assets:
        if asset == "BTC":
            returns = btc_noise
            start = 70000.0
        else:
            beta = 0.85 if asset in {"ETH", "SOL", "AVAX", "BCH"} else 0.20
            idio = rng.normal(0, 0.0012 if beta < 0.5 else 0.0009, size=minutes)
            if asset in {"XPL", "CC", "FARTCOIN"} and minutes > 80:
                low = max(30, min(300, minutes // 3))
                high = max(low + 1, minutes - 40)
                shock_at = int(rng.integers(low=low, high=high))
                idio[shock_at : min(shock_at + 8, minutes)] += rng.choice([-1, 1]) * 0.004
            returns = beta * btc_noise + idio
            start = float(rng.uniform(0.5, 200.0))
        closes = start * np.exp(np.cumsum(returns))
        for ts, close in zip(timestamps, closes):
            rows.append({"timestamp": ts, "asset": asset, "close": float(close)})
    return pd.DataFrame(rows).sort_values(["timestamp", "asset"]).reset_index(drop=True)
