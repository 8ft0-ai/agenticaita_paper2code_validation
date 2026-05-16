The paper does **not** require a prebuilt training dataset. AGENTICAITA is training-free; it needs **live or historical exchange market data** plus a local SQLite memory store. The required inputs are listed in the methodology: 20-bar 1-minute OHLCV candles, live L2 orderbook, funding rate, market snapshot, BTC correlation data for CBD, and episodic memory from past trades. 

You can get the data from these places:

| Required data            | Where to get it                                                                        | Used for                      |
| ------------------------ | -------------------------------------------------------------------------------------- | ----------------------------- |
| 1-minute OHLCV candles   | Exchange API via `ccxt`, e.g. Binance Futures, Bybit, OKX, Hyperliquid-compatible APIs | AZTE trigger, Analyst context |
| L2 orderbook             | Exchange REST/WebSocket API, `fetch_order_book()` in `ccxt`                            | Analyst reasoning             |
| Funding rate             | Perpetual futures exchange API, `fetch_funding_rate()` where supported                 | Analyst context               |
| Ticker / market snapshot | Exchange API, `fetch_ticker()`                                                         | Entry price and context       |
| BTC price history        | Same exchange OHLCV for `BTC/USDT` or `BTC/USDC`                                       | CBD decorrelation score       |
| Volatility history       | Your own SQLite `vol_history` table                                                    | Rolling z-score baseline      |
| Past trade memory        | Your own SQLite `trades` table                                                         | Episodic memory               |

For the code I gave, the easiest live-data option is `ccxt`:

```bash
pip install ccxt
```

Example:

```python
import ccxt

exchange = ccxt.binanceusdm({
    "enableRateLimit": True,
    "options": {"defaultType": "future"},
})

symbol = "BTC/USDT"

ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1m", limit=40)
orderbook = exchange.fetch_order_book(symbol, limit=20)
ticker = exchange.fetch_ticker(symbol)

try:
    funding = exchange.fetch_funding_rate(symbol)
except Exception:
    funding = {"fundingRate": 0.0}

print(ohlcv[-1])
print(orderbook["bids"][:3])
print(ticker["last"])
print(funding.get("fundingRate"))
```

For offline testing or backtesting, use historical 1-minute candles from exchange data portals, Kaggle crypto datasets, CryptoDataDownload, Kaiko, CoinAPI, Polygon, or your own recorded WebSocket stream. The paper’s `vol_history` and `trades` tables are not downloaded from anywhere; they are created by the bot during execution. The rolling baseline only needs about 30 minutes of price observations before AZTE becomes fully active.

---

# Date Range

The paper’s evaluation covers a **five‑day** live session. In the methodology section, the authors explain that they ran AGENTICAITA in DRY_RUN mode on a decentralized perpetual‑futures exchange between **April 6 and April 11, 2026**. They recorded 139 trades across 76 assets during this period and used 1‑minute OHLCV candles, funding rates and orderbook snapshots with a rolling 30‑bar window for the AZTE trigger. To replicate the paper’s results, you would therefore need to collect the same level of market data—from your chosen exchange(s)—covering the entire **April 6–11 2026** window.

---

# Symbols

Use **Hyperliquid perpetuals** as the closest practical match.

The paper only says “a decentralized perpetual futures exchange with over 150 active markets”; it does **not** name the exchange. It also says the system had volatility history for **117 monitored assets**, with **76 assets** generating trades.  So the best replication target is:

```bash
exchange = hyperliquid
date_range = 2026-04-06 to 2026-04-11
timeframe = 1m
market_type = perpetual
```

Use **all available perpetual symbols** from that exchange during the window, not just BTC/ETH/SOL. That is closest to the paper’s setup.

For a smaller first run, use this subset:

```python
SYMBOLS = [
    "BTC/USDC:USDC",
    "ETH/USDC:USDC",
    "SOL/USDC:USDC",
    "AVAX/USDC:USDC",
    "DOGE/USDC:USDC",
    "ADA/USDC:USDC",
    "XRP/USDC:USDC",
    "DOT/USDC:USDC",

    # Symbols explicitly discussed in the paper examples/results
    "FARTCOIN/USDC:USDC",
    "XPL/USDC:USDC",
    "CC/USDC:USDC",
    "HEMI/USDC:USDC",
    "S/USDC:USDC",
    "BCH/USDC:USDC",
    "ETC/USDC:USDC",
]
```

Symbol formatting depends on `ccxt`. For Hyperliquid, the actual market names may differ, so safer code is:

```python
import ccxt

exchange = ccxt.hyperliquid({
    "enableRateLimit": True,
})

markets = exchange.load_markets()

perp_symbols = [
    symbol
    for symbol, market in markets.items()
    if market.get("swap") and market.get("active")
]

print(len(perp_symbols))
print(perp_symbols[:30])
```

Then use:

```python
BTC_SYMBOL = next(s for s in perp_symbols if s.startswith("BTC/"))
SYMBOLS = perp_symbols
```

If Hyperliquid historical OHLCV is incomplete through `ccxt`, use **Binance USD-M futures** or **Bybit USDT perpetuals** for the reconstruction. That will not match the paper’s DEX setting, but it will let you validate the AZTE, CBD, SDP, and IGP logic.

Recommended setup:

```python
EXCHANGE_ID = "hyperliquid"      # closest to paper
# fallback: "binanceusdm" or "bybit"

START = "2026-04-06T00:00:00Z"
END   = "2026-04-11T23:59:59Z"
TIMEFRAME = "1m"
```

For a faithful replication attempt, fetch:

```text
All active perp symbols
BTC perp candles
1-minute OHLCV
Funding history
Ticker snapshots if available
Orderbook snapshots only if you recorded them live
```

The original historical L2 orderbooks, original LLM decisions, and original SQLite logs are not recoverable from public APIs unless the authors release them.
