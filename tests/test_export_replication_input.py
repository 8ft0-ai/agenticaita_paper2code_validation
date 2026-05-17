from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from scripts.export_replication_input import base_asset_from_symbol, load_replication_rows, write_replication_input


def create_candle_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE candles (
                exchange_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp_ms INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO candles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("binanceusdm", "ETH/USDT:USDT", "1m", 60_000, "1970-01-01T00:01:00Z", 10, 12, 9, 11, 100),
                ("binanceusdm", "BTC/USDT:USDT", "1m", 0, "1970-01-01T00:00:00Z", 20, 22, 19, 21, 200),
                ("hyperliquid", "BTC/USDC:USDC", "1m", 0, "1970-01-01T00:00:00Z", 30, 32, 29, 31, 300),
                ("binanceusdm", "BTC/USDT:USDT", "5m", 0, "1970-01-01T00:00:00Z", 40, 42, 39, 41, 400),
            ],
        )


def test_base_asset_from_symbol_normalizes_common_perp_symbols() -> None:
    assert base_asset_from_symbol("BTC/USDT:USDT") == "BTC"
    assert base_asset_from_symbol("ETH/USDC:USDC") == "ETH"
    assert base_asset_from_symbol("SOL") == "SOL"


def test_export_close_only_replication_input(tmp_path) -> None:
    db_path = tmp_path / "market_data.sqlite"
    out_path = tmp_path / "replication_input.csv"
    create_candle_db(db_path)

    with sqlite3.connect(db_path) as conn:
        rows = load_replication_rows(conn, exchange_id="binanceusdm", timeframe="1m", full_ohlcv=False)
    write_replication_input(rows, out_path, full_ohlcv=False)

    with out_path.open(newline="", encoding="utf-8") as handle:
        output = list(csv.DictReader(handle))

    assert output == [
        {"timestamp": "1970-01-01T00:00:00Z", "asset": "BTC", "close": "21.0"},
        {"timestamp": "1970-01-01T00:01:00Z", "asset": "ETH", "close": "11.0"},
    ]


def test_export_full_ohlcv_replication_input(tmp_path) -> None:
    db_path = tmp_path / "market_data.sqlite"
    out_path = tmp_path / "replication_input_ohlcv.csv"
    create_candle_db(db_path)

    with sqlite3.connect(db_path) as conn:
        rows = load_replication_rows(
            conn,
            exchange_id="binanceusdm",
            timeframe="1m",
            symbols=["ETH/USDT:USDT"],
            full_ohlcv=True,
        )
    write_replication_input(rows, out_path, full_ohlcv=True)

    with out_path.open(newline="", encoding="utf-8") as handle:
        output = list(csv.DictReader(handle))

    assert output == [
        {
            "timestamp": "1970-01-01T00:01:00Z",
            "asset": "ETH",
            "open": "10.0",
            "high": "12.0",
            "low": "9.0",
            "close": "11.0",
            "volume": "100.0",
        }
    ]
