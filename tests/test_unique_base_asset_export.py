from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

from scripts.export_replication_input import complete_symbols_from_sqlite, select_unique_base_symbols


def create_complete_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE candles (
                exchange_id TEXT, symbol TEXT, timeframe TEXT, timestamp_ms INTEGER,
                timestamp TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL
            )
            """
        )
        rows = []
        for symbol in [
            "BTC/USD:BTC",
            "BTC/USDC:USDC",
            "BTC/USDT:USDT",
            "ETH/USDC:USDC",
            "ETH/USDT:USDT",
            "SOL/USDT:USDT",
        ]:
            for ts in (0, 60_000, 120_000):
                rows.append(("binanceusdm", symbol, "1m", ts, f"1970-01-01T00:{ts // 60000:02d}:00Z", 1, 2, 0.5, 1.5, 10))
        conn.executemany("INSERT INTO candles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)


def test_unique_selection_deduplicates_before_limit() -> None:
    selected = select_unique_base_symbols(
        ["ETH/USDC:USDC", "BTC/USDC:USDC", "ETH/USDT:USDT", "SOL/USDT:USDT", "BTC/USDT:USDT"],
        symbol_limit=3,
        required_symbol="BTC/USDT:USDT",
    )

    assert selected == ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]
    assert len({symbol.split("/", 1)[0] for symbol in selected}) == 3


def test_explicit_required_contract_wins_duplicate_asset() -> None:
    selected = select_unique_base_symbols(
        ["BTC/USDT:USDT", "BTC/USDC:USDC", "ETH/USDT:USDT"],
        symbol_limit=2,
        required_symbol="BTC/USDC:USDC",
    )

    assert selected == ["BTC/USDC:USDC", "ETH/USDT:USDT"]


def test_complete_selection_returns_unique_assets_and_prioritises_btc(tmp_path: Path) -> None:
    db = tmp_path / "market.sqlite"
    create_complete_db(db)

    with sqlite3.connect(db) as conn:
        selected = complete_symbols_from_sqlite(
            conn,
            exchange_id="binanceusdm",
            timeframe="1m",
            start_ms=0,
            end_ms=120_000,
            symbol_limit=3,
            required_symbol="BTC/USDT:USDT",
            unique_base_assets=True,
        )

    assert selected == ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]


def test_large_profile_dry_run_enables_unique_asset_policy(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_real_data_replication.py",
            "--profile",
            "large",
            "--symbol-limit",
            "76",
            "--skip-fetch",
            "--dry-run",
            "--market-db",
            str(tmp_path / "market.sqlite"),
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert '"selection_policy": "unique_base_assets"' in result.stdout
    assert "--unique-base-assets" in result.stdout
    assert "complete_assets_76.txt" in result.stdout
