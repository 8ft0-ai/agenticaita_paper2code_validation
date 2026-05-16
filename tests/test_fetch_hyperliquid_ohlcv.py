from __future__ import annotations

import csv
import contextlib
import io
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from scripts.fetch_hyperliquid_ohlcv import (
    fetch_symbol_candles,
    resolve_active_swap_symbols,
    run_download,
    select_symbols,
)


class FakeExchange:
    rateLimit = 0

    def __init__(self) -> None:
        self.calls: list[tuple[str, int | None]] = []
        self.markets = {
            "BTC/USDC:USDC": {"symbol": "BTC/USDC:USDC", "swap": True, "active": True},
            "ETH/USDC:USDC": {"symbol": "ETH/USDC:USDC", "type": "swap", "active": True},
            "OLD/USDC:USDC": {"symbol": "OLD/USDC:USDC", "swap": True, "active": False},
            "SPOT/USDC": {"symbol": "SPOT/USDC", "spot": True, "active": True},
        }

    def load_markets(self):
        return self.markets

    def fetch_ohlcv(self, symbol, timeframe="1m", since=None, limit=1000):
        self.calls.append((symbol, since))
        if symbol == "ETH/USDC:USDC":
            raise RuntimeError("temporary exchange failure")
        rows = [
            [0, 1, 2, 0.5, 1.5, 10],
            [60_000, 1.5, 2.5, 1.0, 2.0, 11],
            [120_000, 2.0, 3.0, 1.5, 2.5, 12],
        ]
        return [row for row in rows if row[0] >= since][:limit]


class FetchHyperliquidOhlcvTests(unittest.TestCase):
    def test_resolves_only_active_swap_symbols(self) -> None:
        symbols = resolve_active_swap_symbols(FakeExchange().load_markets())
        self.assertEqual(symbols, ["BTC/USDC:USDC", "ETH/USDC:USDC"])

    def test_select_symbols_supports_subset_and_limit(self) -> None:
        all_symbols = ["BTC/USDC:USDC", "ETH/USDC:USDC", "SOL/USDC:USDC"]
        self.assertEqual(select_symbols(all_symbols, "ETH/USDC:USDC", None), ["ETH/USDC:USDC"])
        self.assertEqual(select_symbols(all_symbols, None, 2), ["BTC/USDC:USDC", "ETH/USDC:USDC"])
        with self.assertRaises(ValueError):
            select_symbols(all_symbols, "MISSING/USDC:USDC", None)

    def test_fetch_symbol_candles_paginates_and_bounds_results(self) -> None:
        exchange = FakeExchange()
        candles, error = fetch_symbol_candles(exchange, "BTC/USDC:USDC", "1m", 0, 120_000, 2, 0, 0)
        self.assertIsNone(error)
        self.assertEqual([row[0] for row in candles], [0, 60_000, 120_000])
        self.assertEqual(exchange.calls, [("BTC/USDC:USDC", 0), ("BTC/USDC:USDC", 120_000)])

    def test_run_download_writes_outputs_and_continues_after_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = Namespace(
                exchange="hyperliquid",
                timeframe="1m",
                start="1970-01-01T00:00:00Z",
                end="1970-01-01T00:02:00Z",
                out=tmp,
                symbols="BTC/USDC:USDC,ETH/USDC:USDC",
                symbol_limit=None,
                limit=2,
                max_retries=0,
                retry_sleep=0,
            )
            with contextlib.redirect_stdout(io.StringIO()):
                manifest = run_download(FakeExchange(), args)

            self.assertEqual([item["symbol"] for item in manifest["successes"]], ["BTC/USDC:USDC"])
            self.assertEqual([item["symbol"] for item in manifest["failures"]], ["ETH/USDC:USDC"])
            self.assertIn("temporary exchange failure", manifest["failures"][0]["error"])

            manifest_path = Path(tmp) / "manifest.json"
            with manifest_path.open(encoding="utf-8") as handle:
                persisted_manifest = json.load(handle)
            self.assertEqual(persisted_manifest["requested_symbols"], ["BTC/USDC:USDC", "ETH/USDC:USDC"])

            with (Path(tmp) / "BTC_USDC_USDC.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["timestamp_ms"] for row in rows], ["0", "60000", "120000"])


if __name__ == "__main__":
    unittest.main()
