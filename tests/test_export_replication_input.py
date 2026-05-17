from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from scripts.export_replication_input import base_asset_from_symbol, complete_symbols_from_sqlite, load_replication_rows, table_exists, write_replication_input


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
        conn.execute(
            """
            CREATE TABLE funding_rates (
                exchange_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timestamp_ms INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                funding_rate REAL,
                retrieved_at TEXT NOT NULL
            )
            """
        )
        conn.executemany(
            "INSERT INTO funding_rates VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("binanceusdm", "BTC/USDT:USDT", 0, "1970-01-01T00:00:00Z", 0.0001, "1970-01-01T00:00:01Z"),
                ("binanceusdm", "ETH/USDT:USDT", 60_000, "1970-01-01T00:01:00Z", -0.0002, "1970-01-01T00:01:01Z"),
            ],
        )


def create_coverage_db(path: Path) -> None:
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
        rows = []
        for symbol in ["ETH/USDT:USDT", "BTC/USDT:USDT", "SOL/USDT:USDT"]:
            timestamps = [0, 60_000, 120_000]
            if symbol == "SOL/USDT:USDT":
                timestamps = [0, 120_000]
            for ts in timestamps:
                rows.append(("binanceusdm", symbol, "1m", ts, f"1970-01-01T00:{ts // 60000:02d}:00Z", 1, 2, 0.5, 1.5, 10))
        conn.executemany("INSERT INTO candles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)


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
        {
            "timestamp": "1970-01-01T00:00:00Z",
            "asset": "BTC",
            "exchange_id": "binanceusdm",
            "source_symbol": "BTC/USDT:USDT",
            "timeframe": "1m",
            "close": "21.0",
        },
        {
            "timestamp": "1970-01-01T00:01:00Z",
            "asset": "ETH",
            "exchange_id": "binanceusdm",
            "source_symbol": "ETH/USDT:USDT",
            "timeframe": "1m",
            "close": "11.0",
        },
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
            "exchange_id": "binanceusdm",
            "source_symbol": "ETH/USDT:USDT",
            "timeframe": "1m",
            "open": "10.0",
            "high": "12.0",
            "low": "9.0",
            "close": "11.0",
            "volume": "100.0",
        }
    ]


def test_export_replication_input_can_include_funding_rates(tmp_path) -> None:
    db_path = tmp_path / "market_data.sqlite"
    out_path = tmp_path / "replication_input.csv"
    create_candle_db(db_path)

    with sqlite3.connect(db_path) as conn:
        rows = load_replication_rows(conn, exchange_id="binanceusdm", timeframe="1m", full_ohlcv=False, include_funding=True)
    write_replication_input(rows, out_path, full_ohlcv=False, include_funding=True)

    with out_path.open(newline="", encoding="utf-8") as handle:
        output = list(csv.DictReader(handle))

    assert output[0]["source_symbol"] == "BTC/USDT:USDT"
    assert output[0]["funding_rate"] == "0.0001"
    assert output[1]["source_symbol"] == "ETH/USDT:USDT"
    assert output[1]["funding_rate"] == "-0.0002"


def test_export_replication_input_marks_funding_blank_when_table_missing(tmp_path) -> None:
    db_path = tmp_path / "coverage.sqlite"
    create_coverage_db(db_path)

    with sqlite3.connect(db_path) as conn:
        assert not table_exists(conn, "funding_rates")
        rows = load_replication_rows(conn, exchange_id="binanceusdm", timeframe="1m", symbols=["BTC/USDT:USDT"], include_funding=True)

    assert rows
    assert {row["funding_rate"] for row in rows} == {""}


def test_complete_symbols_selects_full_coverage_and_prioritizes_required_symbol(tmp_path) -> None:
    db_path = tmp_path / "coverage.sqlite"
    create_coverage_db(db_path)

    with sqlite3.connect(db_path) as conn:
        symbols = complete_symbols_from_sqlite(
            conn,
            exchange_id="binanceusdm",
            timeframe="1m",
            start_ms=0,
            end_ms=120_000,
            symbol_limit=2,
            required_symbol="BTC/USDT:USDT",
        )

    assert symbols == ["BTC/USDT:USDT", "ETH/USDT:USDT"]


def test_complete_symbols_respects_requested_symbol_filter(tmp_path) -> None:
    db_path = tmp_path / "coverage.sqlite"
    create_coverage_db(db_path)

    with sqlite3.connect(db_path) as conn:
        symbols = complete_symbols_from_sqlite(
            conn,
            exchange_id="binanceusdm",
            timeframe="1m",
            start_ms=0,
            end_ms=120_000,
            symbols=["SOL/USDT:USDT", "ETH/USDT:USDT"],
        )

    assert symbols == ["ETH/USDT:USDT"]
