from __future__ import annotations

import csv
import json
import sqlite3
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from scripts.compute_azte_cbd_metrics import Candle, compute_symbol_rows, run_metrics
from scripts.fetch_hyperliquid_ohlcv import init_storage, store_candles, store_symbol_catalog


def make_candles(prices: list[float]) -> list[list[float]]:
    return [[index * 60_000, price, price, price, price, 1.0] for index, price in enumerate(prices)]


class ComputeAzteCbdMetricsTests(unittest.TestCase):
    def test_compute_symbol_rows_marks_warmup_triggers_and_cbd(self) -> None:
        prices = [100.0, 100.01, 100.02, 100.03, 100.04, 100.80]
        candles = [Candle(index * 60_000, f"t{index}", price) for index, price in enumerate(prices)]
        btc_by_ts = {candle.timestamp_ms: Candle(candle.timestamp_ms, candle.timestamp, 10_000 + index) for index, candle in enumerate(candles)}

        rows = compute_symbol_rows(
            "ETH/USDC:USDC",
            candles,
            btc_by_ts,
            window=3,
            z_threshold=2.0,
            absolute_return_floor=0.003,
            cbd_alpha=0.5,
            cbd_kappa=0.5,
        )

        self.assertEqual(len(rows), 5)
        self.assertEqual([row["warmup"] for row in rows[:3]], [True, True, True])
        self.assertTrue(rows[-1]["triggered"])
        self.assertEqual(rows[-1]["trigger_reason"], "z_score_and_abs_return_floor")
        self.assertEqual(rows[-1]["cbd_status"], "computed")
        self.assertIsNotNone(rows[-1]["correlation_to_btc"])
        self.assertIsNotNone(rows[-1]["rho_cb"])
        self.assertIsNotNone(rows[-1]["z_tilde"])
        self.assertIsNotNone(rows[-1]["omega"])

    def test_run_metrics_writes_event_and_summary_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market_data.sqlite"
            conn = init_storage(db_path)
            markets = {
                "BTC/USDC:USDC": {"symbol": "BTC/USDC:USDC", "swap": True, "active": True},
                "ETH/USDC:USDC": {"symbol": "ETH/USDC:USDC", "swap": True, "active": True},
            }
            store_symbol_catalog(conn, "hyperliquid", markets)
            store_candles(conn, "hyperliquid", "BTC/USDC:USDC", "1m", make_candles([100, 101, 102, 103, 104, 105]))
            store_candles(conn, "hyperliquid", "ETH/USDC:USDC", "1m", make_candles([50, 50.01, 50.02, 50.03, 50.04, 50.50]))
            conn.commit()
            conn.close()

            out_dir = Path(tmp) / "metrics"
            summary = run_metrics(
                Namespace(
                    db=str(db_path),
                    out=str(out_dir),
                    exchange="hyperliquid",
                    timeframe="1m",
                    symbols="ETH/USDC:USDC",
                    btc_symbol="BTC/USDC:USDC",
                    window=3,
                    z_threshold=2.0,
                    absolute_return_floor=0.003,
                    cbd_alpha=0.5,
                    cbd_kappa=0.5,
                    per_symbol=False,
                )
            )

            self.assertEqual(summary["total_rows"], 5)
            self.assertEqual(summary["total_triggers"], 1)
            with (out_dir / "azte_cbd_events.csv").open(newline="", encoding="utf-8") as handle:
                events = list(csv.DictReader(handle))
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["symbol"], "ETH/USDC:USDC")
            self.assertEqual(events[0]["triggered"], "true")
            self.assertEqual(events[0]["cbd_status"], "computed")

            with (out_dir / "azte_cbd_summary.json").open(encoding="utf-8") as handle:
                persisted_summary = json.load(handle)
            self.assertEqual(persisted_summary["symbols"][0]["trigger_count"], 1)

    def test_run_metrics_auto_uses_stored_btc_when_subset_excludes_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market_data.sqlite"
            conn = init_storage(db_path)
            markets = {
                "BTC/USDC:USDC": {"symbol": "BTC/USDC:USDC", "swap": True, "active": True},
                "ETH/USDC:USDC": {"symbol": "ETH/USDC:USDC", "swap": True, "active": True},
            }
            store_symbol_catalog(conn, "hyperliquid", markets)
            store_candles(conn, "hyperliquid", "BTC/USDC:USDC", "1m", make_candles([100, 101, 102, 103, 104, 105]))
            store_candles(conn, "hyperliquid", "ETH/USDC:USDC", "1m", make_candles([50, 50.01, 50.02, 50.03, 50.04, 50.50]))
            conn.commit()
            conn.close()

            summary = run_metrics(
                Namespace(
                    db=str(db_path),
                    out=str(Path(tmp) / "metrics"),
                    exchange="hyperliquid",
                    timeframe="1m",
                    symbols="ETH/USDC:USDC",
                    btc_symbol=None,
                    window=3,
                    z_threshold=2.0,
                    absolute_return_floor=0.003,
                    cbd_alpha=0.5,
                    cbd_kappa=0.5,
                    per_symbol=False,
                )
            )

            self.assertEqual(summary["btc_symbol"], "BTC/USDC:USDC")
            self.assertGreater(summary["symbols"][0]["cbd_computed_rows"], 0)


if __name__ == "__main__":
    unittest.main()
