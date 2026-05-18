from __future__ import annotations

import csv
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def create_market_db(path: Path) -> None:
    start = datetime(2026, 4, 6, tzinfo=timezone.utc)
    rows = []
    for symbol, price in (("BTC/USDT:USDT", 70000.0), ("ETH/USDT:USDT", 3000.0)):
        for minute in range(3):
            ts = start + timedelta(minutes=minute)
            rows.append(("binanceusdm", symbol, "1m", int(ts.timestamp() * 1000), ts.isoformat().replace("+00:00", "Z"), price, price + 2, price - 1, price + 1, 100))
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE candles (exchange_id TEXT, symbol TEXT, timeframe TEXT, timestamp_ms INTEGER, timestamp TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)")
        conn.executemany("INSERT INTO candles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)


def test_real_data_workflow_exports_input_from_existing_sqlite(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    db = tmp_path / "market_data.sqlite"
    output = tmp_path / "replication_input_ohlcv.csv"
    symbols = tmp_path / "symbols.txt"
    create_market_db(db)

    result = subprocess.run(
        [sys.executable, "scripts/run_real_data_replication.py", "--skip-fetch", "--skip-replication", "--exchange", "binanceusdm", "--start", "2026-04-06T00:00:00Z", "--end", "2026-04-06T00:02:00Z", "--market-db", str(db), "--replication-input", str(output), "--symbols-out", str(symbols)],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "scripts/export_replication_input.py" in result.stdout
    assert "wrote 6 rows across 2 selected symbols" in result.stdout
    assert symbols.read_text(encoding="utf-8").splitlines() == ["BTC/USDT:USDT", "ETH/USDT:USDT"]
    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 6
    assert rows[0]["asset"] == "BTC"
    assert rows[0]["source_symbol"] == "BTC/USDT:USDT"
    assert {"open", "high", "low", "close", "volume"}.issubset(rows[0])
