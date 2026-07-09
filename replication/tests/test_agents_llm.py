from __future__ import annotations
import sqlite3
from pathlib import Path
import pytest
from src.agenticaita.agents_llm import LLMAnalyst, LLMRiskManager, VolatilityRegimeConfig, analyst_json, risk_json, volatility_regime
from src.agenticaita.azte import TriggerEvent
from src.agenticaita.cbd import CBDResult
from src.agenticaita.contracts import AnalystDecision
from src.agenticaita.llm import LLMError
from src.agenticaita.risk import RiskConfig
from src.agenticaita.simulator import PipelineSimulator, SimulatorConfig, write_sqlite

class FakeProvider:
    def __init__(self, responses=None, error=None):
        self.responses, self.error, self.calls = responses or [], error, []
    def complete(self, system_prompt, user_message):
        self.calls.append((system_prompt, user_message))
        if self.error: raise self.error
        return self.responses.pop(0)

def ev(): return TriggerEvent("2026-04-06T00:31:00Z", "BTC", 100, 0.004, 0.004, 0.001, 0.001, 3, "z_score")
def cb(): return CBDResult(0.39, 0.2, 0.8, 0.6)

def test_llm_analyst_contract_memory_and_fallback():
    p = FakeProvider([{"signal":"long","confidence":0.7,"entry_price":100,"stop_loss":99,"take_profit":102,"size_usd":188,"reasoning":"Composite score 0.60, active volatility regime, orderbook context unavailable."}])
    d = LLMAnalyst(p).decide(ev(), cb(), ["prior BTC reasoning"])
    assert d == AnalystDecision("BTC", "long", 0.7, 100.0, 99.0, 102.0, 188.0, 0.6, 3, d.reasoning)
    assert "prior BTC reasoning" in p.calls[0][1]
    assert LLMAnalyst(FakeProvider(error=LLMError("bad json"))).decide(ev(), cb()).signal in {"long", "short", "wait"}


def test_analyst_json_reports_field_level_validation_errors():
    payload = {"signal":"long","confidence":0.7,"entry_price":100,"stop_loss":"N/A","take_profit":102,"size_usd":188,"reasoning":"ok"}
    with pytest.raises(ValueError, match="stop_loss must be numeric"):
        analyst_json(payload, ev(), cb())

    payload = {"signal":"long","confidence":0.7,"entry_price":100,"stop_loss":0,"take_profit":102,"size_usd":188,"reasoning":"ok"}
    with pytest.raises(ValueError, match="stop_loss must be greater than 0.0"):
        analyst_json(payload, ev(), cb())

    payload = {"signal":"long","confidence":0.7,"entry_price":100,"stop_loss":99,"take_profit":-1,"size_usd":188,"reasoning":"ok"}
    with pytest.raises(ValueError, match="take_profit must be greater than 0.0"):
        analyst_json(payload, ev(), cb())


def test_llm_agents_accept_configurable_prompts_and_volatility_regime():
    p = FakeProvider([{"signal":"long","confidence":0.7,"entry_price":100,"stop_loss":99,"take_profit":102,"size_usd":188,"reasoning":"Composite score 0.60, low volatility regime, orderbook context unavailable."}, {"approved":True,"size_usd":120,"negotiation_summary":"Custom risk prompt accepted."}])
    regime = VolatilityRegimeConfig(high_z_score=10, active_z_score=9, high_abs_return=0.5, active_abs_return=0.4)
    decision = LLMAnalyst(p, system_prompt="custom analyst prompt", volatility_regime_config=regime).decide(ev(), cb())
    LLMRiskManager(p, RiskConfig(confidence_gate=0.6), system_prompt="custom risk prompt").evaluate(decision)
    assert p.calls[0][0] == "custom analyst prompt" and '"volatility_regime": "low"' in p.calls[0][1]
    assert p.calls[1][0] == "custom risk prompt" and volatility_regime(ev(), regime) == "low"


def test_risk_json_reports_field_level_validation_errors():
    with pytest.raises(ValueError, match="approved must be boolean"):
        risk_json({"approved":"maybe","size_usd":100,"negotiation_summary":"ok"}, RiskConfig())

    with pytest.raises(ValueError, match="size_usd must be at most 500.0"):
        risk_json({"approved":True,"size_usd":501,"negotiation_summary":"ok"}, RiskConfig(max_position_size_usd=500.0))

    with pytest.raises(ValueError, match="negotiation_summary must be a non-empty string"):
        risk_json({"approved":True,"size_usd":100,"negotiation_summary":""}, RiskConfig())


def test_llm_risk_manager_preserves_hard_gate_and_uses_layer_b():
    p = FakeProvider([{"approved":True,"size_usd":120,"negotiation_summary":"Reduced size for proportional balancing."}])
    m = LLMRiskManager(p, RiskConfig(confidence_gate=0.6))
    assert not m.evaluate(AnalystDecision("BTC","wait",0.9,100,100,100,188,0.6,3,"wait")).approved
    assert p.calls == []
    r = m.evaluate(AnalystDecision("BTC","long",0.9,100,99,102,188,0.6,3,"test"))
    assert r.approved and r.size_usd == 120.0 and len(p.calls) == 1


def test_pipeline_memory_and_sqlite(tmp_path: Path):
    pd = pytest.importorskip("pandas")
    p = FakeProvider([
        {"signal":"long","confidence":0.9,"entry_price":100.5,"stop_loss":99.5,"take_profit":102,"size_usd":100,"reasoning":"Composite score first, active volatility regime, orderbook context unavailable."},
        {"approved":True,"size_usd":100,"negotiation_summary":"Approved first."},
        {"signal":"long","confidence":0.9,"entry_price":101.2,"stop_loss":100.2,"take_profit":103,"size_usd":100,"reasoning":"Composite score second, active volatility regime, orderbook context unavailable."},
        {"approved":True,"size_usd":100,"negotiation_summary":"Approved second."},
    ])
    sim = PipelineSimulator(SimulatorConfig(rolling_window=3,z_threshold=99,absolute_return_floor=0.003,global_cooldown_seconds=0,per_asset_cooldown_seconds=0,benchmark_asset="BTC",exit_horizon_minutes=1), analyst_agent=LLMAnalyst(p), risk_manager=LLMRiskManager(p), episodic_memory_depth=5)
    df = pd.DataFrame([{"timestamp":f"2026-04-06T00:0{i}:00Z","asset":"BTC","close":c} for i,c in enumerate([100,100.01,100.02,100.03,100.5,101.2,101.3])])
    log, trades, vol = sim.run(df)
    assert "Composite score first" in p.calls[2][1] and "agent_warnings" in log.columns
    db = tmp_path / "run.sqlite"; write_sqlite(db, log, trades, vol)
    with sqlite3.connect(db) as conn:
        tables = set(pd.read_sql_query("select name from sqlite_master where type='table'", conn)["name"])
    assert {"pipeline_log", "trades", "vol_history"}.issubset(tables)
