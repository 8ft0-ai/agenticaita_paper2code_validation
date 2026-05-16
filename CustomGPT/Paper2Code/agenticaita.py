from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple

import numpy as np
import requests


# -----------------------------
# Config
# -----------------------------

@dataclass
class Config:
    db_path: str = "agenticaita.sqlite"

    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
    ollama_timeout_s: int = 90
    llm_temperature: float = 0.1

    dry_run: bool = True

    polling_interval_s: int = 60
    z_window: int = 30
    z_threshold: float = 2.0
    abs_return_floor: float = 0.003

    confidence_gate: float = 0.60
    max_risk_per_trade: float = 0.02
    max_position_size_usd: float = 500.0

    per_asset_cooldown_s: int = 300
    igp_cooldown_s: int = 1800

    cbd_alpha: float = 0.5
    cbd_kappa: float = 0.5

    btc_symbol: str = "BTC/USDT"
    watch_symbols: Tuple[str, ...] = ("BTC/USDT", "ETH/USDT", "SOL/USDT")


# -----------------------------
# Typed contracts
# -----------------------------

@dataclass
class TriggerEvent:
    symbol: str
    price: float
    prev_price: Optional[float]
    abs_return: float
    z_score: float
    triggered: bool
    reason: str
    ts: float


@dataclass
class AnalystDecision:
    signal: str
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    size_usd: float
    reasoning: str


@dataclass
class RiskDecision:
    approved: bool
    size_usd: float
    negotiation_summary: str


@dataclass
class ExecutionResult:
    status: str
    order_id: Optional[str]
    detail: Dict[str, Any]


@dataclass
class MarketContext:
    symbol: str
    ohlcv: List[List[float]]       # [timestamp_ms, open, high, low, close, volume]
    orderbook: Dict[str, Any]      # {"bids": [[price, qty], ...], "asks": ...}
    funding_rate: float
    snapshot: Dict[str, Any]

    @property
    def last_price(self) -> float:
        if self.snapshot.get("last") is not None:
            return float(self.snapshot["last"])
        return float(self.ohlcv[-1][4])

    @property
    def closes(self) -> List[float]:
        return [float(x[4]) for x in self.ohlcv]

    @property
    def volumes(self) -> List[float]:
        return [float(x[5]) for x in self.ohlcv]


# -----------------------------
# Utilities
# -----------------------------

def now_ts() -> float:
    return time.time()


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        y = float(x)
        if math.isfinite(y):
            return y
    except Exception:
        pass
    return default


def json_dumps(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"), default=str)


def extract_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        raise


def orderbook_summary(orderbook: Dict[str, Any], depth: int = 10) -> Dict[str, Any]:
    bids = orderbook.get("bids", [])[:depth]
    asks = orderbook.get("asks", [])[:depth]

    best_bid = safe_float(bids[0][0]) if bids else 0.0
    best_ask = safe_float(asks[0][0]) if asks else 0.0
    mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0.0
    spread = best_ask - best_bid if best_bid and best_ask else 0.0
    spread_bps = spread / mid * 1e4 if mid else 0.0

    bid_depth = sum(safe_float(q) for _, q in bids)
    ask_depth = sum(safe_float(q) for _, q in asks)
    denom = bid_depth + ask_depth
    imbalance = (bid_depth - ask_depth) / denom if denom > 0 else 0.0

    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid": mid,
        "spread": spread,
        "spread_bps": spread_bps,
        "bid_depth": bid_depth,
        "ask_depth": ask_depth,
        "imbalance": imbalance,
        "top_bids": bids[:5],
        "top_asks": asks[:5],
    }


def ohlcv_to_records(ohlcv: List[List[float]], limit: int = 20) -> List[Dict[str, Any]]:
    out = []
    for t, o, h, l, c, v in ohlcv[-limit:]:
        out.append({
            "t": int(t),
            "open": safe_float(o),
            "high": safe_float(h),
            "low": safe_float(l),
            "close": safe_float(c),
            "volume": safe_float(v),
        })
    return out


# -----------------------------
# SQLite episodic memory
# -----------------------------

class MemoryDB:
    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        with self.lock:
            self.conn.execute("PRAGMA journal_mode=WAL;")
            self.conn.execute("PRAGMA busy_timeout=5000;")
            self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.init_schema()

    def init_schema(self) -> None:
        with self.lock:
            self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS vol_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                abs_return REAL NOT NULL,
                z_score REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_vol_symbol_id
            ON vol_history(symbol, id);

            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                symbol TEXT NOT NULL,
                signal TEXT NOT NULL,
                confidence REAL NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                size_usd REAL NOT NULL,
                analyst_reasoning TEXT,
                risk_approved INTEGER NOT NULL,
                rm_size_usd REAL,
                negotiation_summary TEXT,
                status TEXT NOT NULL,
                pnl REAL,
                metadata_json TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_trades_symbol_id
            ON trades(symbol, id);

            CREATE TABLE IF NOT EXISTS pipeline_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                symbol TEXT,
                event TEXT NOT NULL,
                data_json TEXT
            );

            CREATE TABLE IF NOT EXISTS ollama_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                agent TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_chars INTEGER NOT NULL,
                response_chars INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                ok INTEGER NOT NULL,
                error TEXT
            );
            """)
            self.conn.commit()

    def persist_vol(self, symbol: str, price: float, abs_return: float, z_score: float) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT INTO vol_history(ts,symbol,price,abs_return,z_score) VALUES(?,?,?,?,?)",
                (now_ts(), symbol, price, abs_return, z_score),
            )
            self.conn.commit()

    def last_price(self, symbol: str) -> Optional[float]:
        with self.lock:
            row = self.conn.execute(
                "SELECT price FROM vol_history WHERE symbol=? ORDER BY id DESC LIMIT 1",
                (symbol,),
            ).fetchone()
        return float(row["price"]) if row else None

    def last_returns(self, symbol: str, n: int) -> List[float]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT abs_return FROM vol_history WHERE symbol=? ORDER BY id DESC LIMIT ?",
                (symbol, n),
            ).fetchall()
        return [float(r["abs_return"]) for r in rows][::-1]

    def memory_brief(self, symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
        with self.lock:
            rows = self.conn.execute(
                """
                SELECT ts, signal, confidence, entry_price, stop_loss, take_profit,
                       size_usd, status, pnl, analyst_reasoning, negotiation_summary
                FROM trades
                WHERE symbol=?
                ORDER BY id DESC
                LIMIT ?
                """,
                (symbol, limit),
            ).fetchall()

        return [dict(r) for r in rows]

    def log_event(self, symbol: Optional[str], event: str, data: Dict[str, Any]) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT INTO pipeline_log(ts,symbol,event,data_json) VALUES(?,?,?,?)",
                (now_ts(), symbol, event, json_dumps(data)),
            )
            self.conn.commit()

    def log_ollama(
        self,
        agent: str,
        model: str,
        prompt_chars: int,
        response_chars: int,
        latency_ms: float,
        ok: bool,
        error: Optional[str] = None,
    ) -> None:
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO ollama_calls
                (ts,agent,model,prompt_chars,response_chars,latency_ms,ok,error)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (now_ts(), agent, model, prompt_chars, response_chars, latency_ms, int(ok), error),
            )
            self.conn.commit()

    def insert_trade(
        self,
        symbol: str,
        analyst: AnalystDecision,
        risk: Optional[RiskDecision],
        status: str,
        pnl: Optional[float],
        metadata: Dict[str, Any],
    ) -> None:
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO trades
                (ts,symbol,signal,confidence,entry_price,stop_loss,take_profit,size_usd,
                 analyst_reasoning,risk_approved,rm_size_usd,negotiation_summary,status,pnl,metadata_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    now_ts(),
                    symbol,
                    analyst.signal,
                    analyst.confidence,
                    analyst.entry_price,
                    analyst.stop_loss,
                    analyst.take_profit,
                    analyst.size_usd,
                    analyst.reasoning,
                    int(risk.approved) if risk else 0,
                    risk.size_usd if risk else None,
                    risk.negotiation_summary if risk else None,
                    status,
                    pnl,
                    json_dumps(metadata),
                ),
            )
            self.conn.commit()


# -----------------------------
# Market data providers
# -----------------------------

class MarketDataProvider(Protocol):
    def fetch_context(self, symbol: str, limit: int) -> MarketContext:
        ...


class CCXTMarketDataProvider:
    def __init__(self, exchange_id: str = "binanceusdm"):
        import ccxt

        exchange_cls = getattr(ccxt, exchange_id)
        self.exchange = exchange_cls({
            "enableRateLimit": True,
            "apiKey": os.getenv("EXCHANGE_API_KEY", ""),
            "secret": os.getenv("EXCHANGE_SECRET", ""),
            "options": {"defaultType": "future"},
        })
        self.exchange.load_markets()

    def fetch_context(self, symbol: str, limit: int) -> MarketContext:
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe="1m", limit=max(limit, 40))
        orderbook = self.exchange.fetch_order_book(symbol, limit=20)

        ticker = self.exchange.fetch_ticker(symbol)
        funding_rate = 0.0
        try:
            if hasattr(self.exchange, "fetch_funding_rate"):
                fr = self.exchange.fetch_funding_rate(symbol)
                funding_rate = safe_float(fr.get("fundingRate", 0.0))
        except Exception:
            funding_rate = 0.0

        snapshot = {
            "last": ticker.get("last") or ohlcv[-1][4],
            "bid": ticker.get("bid"),
            "ask": ticker.get("ask"),
            "baseVolume": ticker.get("baseVolume"),
            "quoteVolume": ticker.get("quoteVolume"),
        }

        return MarketContext(
            symbol=symbol,
            ohlcv=ohlcv,
            orderbook=orderbook,
            funding_rate=funding_rate,
            snapshot=snapshot,
        )


class SyntheticMarketDataProvider:
    def __init__(self, symbols: Tuple[str, ...], seed: int = 7):
        self.rng = np.random.default_rng(seed)
        self.prices = {s: 100.0 + i * 50.0 for i, s in enumerate(symbols)}
        self.history = {s: [self.prices[s]] * 80 for s in symbols}

    def fetch_context(self, symbol: str, limit: int) -> MarketContext:
        prev = self.prices.get(symbol, 100.0)
        shock = self.rng.normal(0.0, 0.0008)
        if self.rng.random() < 0.05:
            shock += self.rng.normal(0.0, 0.006)
        price = max(0.01, prev * (1.0 + shock))

        self.prices[symbol] = price
        self.history.setdefault(symbol, [price] * 80).append(price)
        self.history[symbol] = self.history[symbol][-200:]

        closes = self.history[symbol][-max(limit, 40):]
        now_ms = int(time.time() * 1000)
        ohlcv = []
        for i, c in enumerate(closes):
            o = closes[i - 1] if i > 0 else c
            high = max(o, c) * (1 + abs(self.rng.normal(0, 0.0006)))
            low = min(o, c) * (1 - abs(self.rng.normal(0, 0.0006)))
            vol = float(abs(self.rng.normal(1000, 250)))
            ohlcv.append([now_ms - (len(closes) - i) * 60_000, o, high, low, c, vol])

        spread = price * 0.0004
        bids = [[price - spread * (i + 1), 10 + i] for i in range(20)]
        asks = [[price + spread * (i + 1), 10 + i] for i in range(20)]

        return MarketContext(
            symbol=symbol,
            ohlcv=ohlcv,
            orderbook={"bids": bids, "asks": asks},
            funding_rate=float(self.rng.normal(0.0, 0.00005)),
            snapshot={"last": price, "bid": bids[0][0], "ask": asks[0][0]},
        )


# -----------------------------
# AZTE: Adaptive Z-score Trigger Engine
# -----------------------------

class AZTE:
    def __init__(self, cfg: Config, db: MemoryDB):
        self.cfg = cfg
        self.db = db

    def update(self, symbol: str, price: float) -> TriggerEvent:
        prev_price = self.db.last_price(symbol)

        if prev_price is None or prev_price <= 0:
            event = TriggerEvent(
                symbol=symbol,
                price=price,
                prev_price=prev_price,
                abs_return=0.0,
                z_score=0.0,
                triggered=False,
                reason="warmup_no_previous_price",
                ts=now_ts(),
            )
            self.db.persist_vol(symbol, price, 0.0, 0.0)
            return event

        abs_return = abs((price - prev_price) / prev_price)
        baseline = self.db.last_returns(symbol, self.cfg.z_window)

        if len(baseline) >= 2:
            mu = float(np.mean(baseline))
            sigma = float(np.std(baseline, ddof=1))
            z = (abs_return - mu) / sigma if sigma > 1e-12 else 0.0
        else:
            z = 0.0

        has_window = len(baseline) >= self.cfg.z_window
        z_trigger = has_window and z >= self.cfg.z_threshold
        floor_trigger = abs_return >= self.cfg.abs_return_floor

        triggered = bool(z_trigger or floor_trigger)
        reason = (
            "z_score"
            if z_trigger
            else "absolute_return_floor"
            if floor_trigger
            else "no_trigger"
        )

        self.db.persist_vol(symbol, price, abs_return, z)

        return TriggerEvent(
            symbol=symbol,
            price=price,
            prev_price=prev_price,
            abs_return=abs_return,
            z_score=z,
            triggered=triggered,
            reason=reason,
            ts=now_ts(),
        )


# -----------------------------
# CBD: Correlation-Break Diversification
# -----------------------------

@dataclass
class CBDResult:
    omega: float
    rho_cb: float
    z_tilde: float
    corr_to_btc: float


class CBD:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def compute(self, asset_prices: List[float], btc_prices: List[float], z_score: float) -> CBDResult:
        n = min(len(asset_prices), len(btc_prices), self.cfg.z_window)
        if n < 3:
            corr = 0.0
            rho_cb = 0.0
        else:
            a = np.asarray(asset_prices[-n:], dtype=float)
            b = np.asarray(btc_prices[-n:], dtype=float)
            if np.std(a) < 1e-12 or np.std(b) < 1e-12:
                corr = 0.0
            else:
                corr = float(np.corrcoef(a, b)[0, 1])
                if not math.isfinite(corr):
                    corr = 0.0
            rho_cb = 1.0 - abs(corr)

        if abs(z_score) >= self.cfg.z_threshold:
            z_tilde = 1.0 - math.exp(-self.cfg.cbd_kappa * (abs(z_score) - self.cfg.z_threshold))
        else:
            z_tilde = 0.0

        omega = self.cfg.cbd_alpha * z_tilde + (1.0 - self.cfg.cbd_alpha) * rho_cb
        return CBDResult(
            omega=clamp(omega, 0.0, 1.0),
            rho_cb=clamp(rho_cb, 0.0, 1.0),
            z_tilde=clamp(z_tilde, 0.0, 1.0),
            corr_to_btc=clamp(corr, -1.0, 1.0),
        )


# -----------------------------
# IGP: Inference Gating Protocol
# -----------------------------

class InferenceGate:
    def __init__(self, cfg: Config, db: MemoryDB):
        self.cfg = cfg
        self.db = db
        self.pipeline_lock = threading.Lock()
        self.state_lock = threading.Lock()
        self.last_global_start = 0.0
        self.last_asset_start: Dict[str, float] = {}

    def try_acquire(self, symbol: str) -> Tuple[bool, str]:
        t = now_ts()

        with self.state_lock:
            if t - self.last_global_start < self.cfg.igp_cooldown_s:
                return False, "igp_global_cooldown"

            if t - self.last_asset_start.get(symbol, 0.0) < self.cfg.per_asset_cooldown_s:
                return False, "per_asset_cooldown"

        if not self.pipeline_lock.acquire(blocking=False):
            return False, "pipeline_busy"

        with self.state_lock:
            self.last_global_start = t
            self.last_asset_start[symbol] = t

        return True, "admitted"

    def release(self) -> None:
        try:
            self.pipeline_lock.release()
        except RuntimeError:
            pass


# -----------------------------
# Ollama JSON client
# -----------------------------

class OllamaJSONClient:
    def __init__(self, cfg: Config, db: MemoryDB):
        self.cfg = cfg
        self.db = db

    def chat_json(self, agent: str, system: str, user: str) -> Dict[str, Any]:
        payload = {
            "model": self.cfg.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": self.cfg.llm_temperature},
        }

        t0 = time.perf_counter()
        ok = False
        content = ""
        error = None

        try:
            resp = requests.post(
                f"{self.cfg.ollama_url.rstrip('/')}/api/chat",
                json=payload,
                timeout=self.cfg.ollama_timeout_s,
            )
            resp.raise_for_status()
            body = resp.json()
            content = body.get("message", {}).get("content", "")
            data = extract_json(content)
            ok = True
            return data
        except Exception as e:
            error = str(e)
            raise
        finally:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            self.db.log_ollama(
                agent=agent,
                model=self.cfg.ollama_model,
                prompt_chars=len(system) + len(user),
                response_chars=len(content),
                latency_ms=latency_ms,
                ok=ok,
                error=error,
            )


# -----------------------------
# Agents
# -----------------------------

class AnalystAgent:
    SYSTEM_PROMPT = """
You are the AgenticAITA Analyst. Analyze the market and produce a trading signal.

Respond ONLY in valid JSON with exactly this schema:
{
  "signal": "long" | "short" | "wait",
  "confidence": float between 0 and 1,
  "entry_price": float,
  "stop_loss": float,
  "take_profit": float,
  "size_usd": float,
  "reasoning": "string"
}

Your reasoning MUST cite:
- the CBD composite score omega,
- the volatility regime and AZTE z-score,
- the orderbook context.

Do not place orders. Do not approve risk. Produce one decision only.
"""

    def __init__(self, cfg: Config, llm: OllamaJSONClient):
        self.cfg = cfg
        self.llm = llm

    def analyze(self, context: Dict[str, Any]) -> AnalystDecision:
        user = json_dumps(context)

        try:
            raw = self.llm.chat_json("analyst", self.SYSTEM_PROMPT, user)
        except Exception as e:
            return AnalystDecision(
                signal="wait",
                confidence=0.0,
                entry_price=safe_float(context.get("market_snapshot", {}).get("last")),
                stop_loss=0.0,
                take_profit=0.0,
                size_usd=0.0,
                reasoning=f"LLM unavailable; conservative wait. error={e}",
            )

        signal = str(raw.get("signal", "wait")).lower().strip()
        if signal not in {"long", "short", "wait"}:
            signal = "wait"

        entry = safe_float(raw.get("entry_price"), safe_float(context.get("market_snapshot", {}).get("last")))
        return AnalystDecision(
            signal=signal,
            confidence=clamp(safe_float(raw.get("confidence"), 0.0), 0.0, 1.0),
            entry_price=entry,
            stop_loss=safe_float(raw.get("stop_loss"), 0.0),
            take_profit=safe_float(raw.get("take_profit"), 0.0),
            size_usd=max(0.0, safe_float(raw.get("size_usd"), 0.0)),
            reasoning=str(raw.get("reasoning", ""))[:4000],
        )


class RiskManagerAgent:
    SYSTEM_PROMPT = """
You are the AgenticAITA Risk Manager. Your goal is Proportional Portfolio Balancing.

The deterministic hard gates have already been applied before this LLM call.
Now perform contextual validation and calibrate size_usd based on the Analyst confidence.

Respond ONLY in valid JSON with exactly this schema:
{
  "approved": boolean,
  "size_usd": float,
  "negotiation_summary": "string"
}
"""

    def __init__(self, cfg: Config, llm: OllamaJSONClient):
        self.cfg = cfg
        self.llm = llm

    def hard_gate(self, d: AnalystDecision) -> Optional[str]:
        if d.signal not in {"long", "short"}:
            return "signal_not_directional"

        if d.confidence < self.cfg.confidence_gate:
            return "confidence_below_gate"

        if d.entry_price <= 0 or d.stop_loss <= 0:
            return "invalid_entry_or_stop"

        risk_frac = abs(d.entry_price - d.stop_loss) / d.entry_price
        if risk_frac > self.cfg.max_risk_per_trade:
            return "stop_risk_exceeds_2_percent"

        if d.size_usd > self.cfg.max_position_size_usd:
            return "size_exceeds_500_usd"

        return None

    def evaluate(self, analyst: AnalystDecision, context: Dict[str, Any]) -> RiskDecision:
        fail = self.hard_gate(analyst)
        if fail:
            return RiskDecision(
                approved=False,
                size_usd=0.0,
                negotiation_summary=f"Rejected by deterministic hard gate: {fail}",
            )

        fallback_size = min(
            self.cfg.max_position_size_usd,
            max(1.0, self.cfg.max_position_size_usd * analyst.confidence),
        )

        user = json_dumps({
            "analyst_decision": asdict(analyst),
            "fallback_size_usd": fallback_size,
            "risk_limits": {
                "confidence_gate": self.cfg.confidence_gate,
                "max_risk_per_trade": self.cfg.max_risk_per_trade,
                "max_position_size_usd": self.cfg.max_position_size_usd,
            },
            "market_context": {
                "symbol": context.get("symbol"),
                "azte": context.get("azte"),
                "cbd": context.get("cbd"),
                "orderbook": context.get("orderbook"),
                "funding_rate": context.get("funding_rate"),
                "market_snapshot": context.get("market_snapshot"),
                "episodic_memory": context.get("episodic_memory"),
            },
        })

        try:
            raw = self.llm.chat_json("risk_manager", self.SYSTEM_PROMPT, user)
            approved = bool(raw.get("approved", False))
            size = safe_float(raw.get("size_usd"), fallback_size)
            summary = str(raw.get("negotiation_summary", ""))[:4000]
        except Exception as e:
            approved = True
            size = fallback_size
            summary = f"LLM unavailable after hard gates; using deterministic fallback size. error={e}"

        return RiskDecision(
            approved=approved,
            size_usd=clamp(size, 0.0, self.cfg.max_position_size_usd),
            negotiation_summary=summary,
        )


# -----------------------------
# Executor
# -----------------------------

class LiveOrderRouter:
    def safe(self) -> bool:
        return False

    def place_order(self, symbol: str, side: str, size_usd: float, price_hint: float) -> Dict[str, Any]:
        raise NotImplementedError("Implement exchange-specific private order routing here.")


class ExecutorAgent:
    def __init__(self, cfg: Config, db: MemoryDB, router: Optional[LiveOrderRouter] = None):
        self.cfg = cfg
        self.db = db
        self.router = router or LiveOrderRouter()

    def execute(
        self,
        symbol: str,
        analyst: AnalystDecision,
        risk: RiskDecision,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        side = "buy" if analyst.signal == "long" else "sell"

        if self.cfg.dry_run:
            result = ExecutionResult(
                status="dry_run_logged",
                order_id=f"dry_{uuid.uuid4().hex[:12]}",
                detail={
                    "side": side,
                    "size_usd": risk.size_usd,
                    "entry_price": analyst.entry_price,
                    "stop_loss": analyst.stop_loss,
                    "take_profit": analyst.take_profit,
                },
            )
            self.db.insert_trade(symbol, analyst, risk, result.status, pnl=None, metadata={
                "execution": asdict(result),
                "context": context,
            })
            self.db.log_event(symbol, "executor_dry_run", asdict(result))
            return result

        if not self.router.safe():
            result = ExecutionResult(
                status="live_blocked_safety_gate",
                order_id=None,
                detail={"reason": "router_safe_false"},
            )
            self.db.insert_trade(symbol, analyst, risk, result.status, pnl=None, metadata={
                "execution": asdict(result),
                "context": context,
            })
            self.db.log_event(symbol, "executor_live_blocked", asdict(result))
            return result

        order = self.router.place_order(symbol, side, risk.size_usd, analyst.entry_price)
        result = ExecutionResult(status="live_order_submitted", order_id=str(order.get("id")), detail=order)

        self.db.insert_trade(symbol, analyst, risk, result.status, pnl=None, metadata={
            "execution": asdict(result),
            "context": context,
        })
        self.db.log_event(symbol, "executor_live_order", asdict(result))
        return result


# -----------------------------
# Slippage / cost model
# -----------------------------

def round_trip_cost_usd(
    size_usd: float,
    price: float,
    bid: float,
    ask: float,
    realized_vol_1m: float,
    avg_volume_base: float,
    taker_fee: float,
    impact_lambda: float = 0.8,
) -> float:
    if price <= 0:
        return 0.0

    qty = size_usd / price
    fee = size_usd * taker_fee
    half_spread = 0.5 * qty * abs(ask - bid) if bid and ask else 0.0

    volume = max(avg_volume_base, 1e-12)
    impact = impact_lambda * realized_vol_1m * math.sqrt(max(qty, 0.0) / volume) * price

    return fee + half_spread + impact


# -----------------------------
# Orchestrator
# -----------------------------

class AgenticAITA:
    def __init__(
        self,
        cfg: Config,
        market: MarketDataProvider,
        router: Optional[LiveOrderRouter] = None,
    ):
        self.cfg = cfg
        self.market = market
        self.db = MemoryDB(cfg.db_path)

        self.azte = AZTE(cfg, self.db)
        self.cbd = CBD(cfg)
        self.igp = InferenceGate(cfg, self.db)

        self.llm = OllamaJSONClient(cfg, self.db)
        self.analyst = AnalystAgent(cfg, self.llm)
        self.risk_manager = RiskManagerAgent(cfg, self.llm)
        self.executor = ExecutorAgent(cfg, self.db, router)

    def build_llm_context(
        self,
        trigger: TriggerEvent,
        market_ctx: MarketContext,
        btc_ctx: MarketContext,
    ) -> Dict[str, Any]:
        cbd = self.cbd.compute(market_ctx.closes, btc_ctx.closes, trigger.z_score)
        ob = orderbook_summary(market_ctx.orderbook)

        recent_closes = np.asarray(market_ctx.closes[-20:], dtype=float)
        realized_vol_1m = float(np.std(np.diff(np.log(recent_closes)))) if len(recent_closes) > 3 else 0.0

        return {
            "symbol": market_ctx.symbol,
            "ohlcv_1m_20": ohlcv_to_records(market_ctx.ohlcv, limit=20),
            "orderbook": ob,
            "funding_rate": market_ctx.funding_rate,
            "market_snapshot": market_ctx.snapshot,
            "azte": asdict(trigger),
            "cbd": asdict(cbd),
            "volatility": {
                "realized_log_return_vol_1m": realized_vol_1m,
                "regime": (
                    "anomalous"
                    if trigger.z_score >= self.cfg.z_threshold
                    else "absolute_move"
                    if trigger.abs_return >= self.cfg.abs_return_floor
                    else "normal"
                ),
            },
            "episodic_memory": self.db.memory_brief(market_ctx.symbol, limit=5),
        }

    def run_pipeline(self, trigger: TriggerEvent, market_ctx: MarketContext) -> None:
        symbol = market_ctx.symbol
        self.db.log_event(symbol, "pipeline_start", asdict(trigger))

        try:
            if symbol == self.cfg.btc_symbol:
                btc_ctx = market_ctx
            else:
                btc_ctx = self.market.fetch_context(self.cfg.btc_symbol, limit=max(self.cfg.z_window, 40))

            context = self.build_llm_context(trigger, market_ctx, btc_ctx)

            analyst_decision = self.analyst.analyze(context)
            self.db.log_event(symbol, "analyst_decision", asdict(analyst_decision))

            if analyst_decision.signal == "wait":
                self.db.insert_trade(
                    symbol,
                    analyst_decision,
                    None,
                    status="analyst_wait",
                    pnl=None,
                    metadata={"context": context},
                )
                self.db.log_event(symbol, "pipeline_end_wait", {"reason": analyst_decision.reasoning})
                return

            risk_decision = self.risk_manager.evaluate(analyst_decision, context)
            self.db.log_event(symbol, "risk_decision", asdict(risk_decision))

            if not risk_decision.approved:
                self.db.insert_trade(
                    symbol,
                    analyst_decision,
                    risk_decision,
                    status="risk_rejected",
                    pnl=None,
                    metadata={"context": context},
                )
                self.db.log_event(symbol, "pipeline_end_rejected", asdict(risk_decision))
                return

            result = self.executor.execute(symbol, analyst_decision, risk_decision, context)
            self.db.log_event(symbol, "pipeline_end_executed", asdict(result))

        except Exception as e:
            self.db.log_event(symbol, "pipeline_error", {"error": str(e)})

    def run_once(self) -> None:
        for symbol in self.cfg.watch_symbols:
            try:
                ctx = self.market.fetch_context(symbol, limit=max(self.cfg.z_window + 1, 40))
                trigger = self.azte.update(symbol, ctx.last_price)

                if not trigger.triggered:
                    continue

                admitted, reason = self.igp.try_acquire(symbol)
                if not admitted:
                    self.db.log_event(symbol, reason, asdict(trigger))
                    continue

                try:
                    self.run_pipeline(trigger, ctx)
                finally:
                    self.igp.release()

            except Exception as e:
                self.db.log_event(symbol, "poll_error", {"error": str(e)})

    def run_forever(self) -> None:
        while True:
            started = time.time()
            self.run_once()
            elapsed = time.time() - started
            time.sleep(max(1.0, self.cfg.polling_interval_s - elapsed))


# -----------------------------
# CLI
# -----------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="agenticaita.sqlite")
    p.add_argument("--exchange", default="synthetic", help="synthetic or ccxt exchange id, e.g. binanceusdm")
    p.add_argument("--symbols", default="BTC/USDT,ETH/USDT,SOL/USDT")
    p.add_argument("--btc-symbol", default="BTC/USDT")
    p.add_argument("--ollama-url", default=os.getenv("OLLAMA_URL", "http://localhost:11434"))
    p.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "qwen3.5:9b"))
    p.add_argument("--once", action="store_true")
    p.add_argument("--live", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    symbols = tuple(s.strip() for s in args.symbols.split(",") if s.strip())

    cfg = Config(
        db_path=args.db,
        ollama_url=args.ollama_url,
        ollama_model=args.model,
        dry_run=not args.live,
        watch_symbols=symbols,
        btc_symbol=args.btc_symbol,
    )

    if args.exchange == "synthetic":
        market: MarketDataProvider = SyntheticMarketDataProvider(tuple(set(symbols + (cfg.btc_symbol,))))
    else:
        market = CCXTMarketDataProvider(args.exchange)

    bot = AgenticAITA(cfg, market)

    if args.once:
        bot.run_once()
    else:
        bot.run_forever()


if __name__ == "__main__":
    main()
