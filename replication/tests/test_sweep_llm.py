from __future__ import annotations

import pytest

from sweep import build_parser, build_simulator, run_sweep
from src.agenticaita.agents_llm import LLMAnalyst, LLMRiskManager


def base_cfg() -> dict:
    return {
        "azte": {"rolling_window": 3, "z_threshold": 99.0, "absolute_return_floor": 0.003},
        "igp": {"global_cooldown_seconds": 0, "per_asset_cooldown_seconds": 0},
        "risk": {
            "confidence_gate": 0.0,
            "max_stop_loss_fraction": 0.02,
            "max_position_size_usd": 500.0,
            "base_position_size_usd": 188.0,
        },
        "cbd": {"alpha": 0.5, "kappa": 0.5, "benchmark_asset": "BTC"},
        "llm": {
            "provider": "openrouter",
            "model": "qwen/test-model",
            "api_key_env": "MISSING_TEST_OPENROUTER_KEY",
            "temperature": 0.0,
            "max_tokens": 64,
            "audit_log_path": None,
            "timeout_seconds": 1,
            "max_retries": 0,
            "retry_backoff_seconds": 0,
        },
        "agents": {
            "analyst": "deterministic",
            "risk_manager": "deterministic",
            "episodic_memory_depth": 5,
            "llm": {
                "volatility_regime": {
                    "high_z_score": 3.0,
                    "active_z_score": 2.0,
                    "high_abs_return": 0.01,
                    "active_abs_return": 0.003,
                },
                "prompts": {"analyst_system_prompt": None, "risk_system_prompt": None},
            },
        },
    }


def triggered_ohlcv():
    pd = pytest.importorskip("pandas")
    return pd.DataFrame(
        [
            {"timestamp": f"2026-04-06T00:0{i}:00Z", "asset": "BTC", "close": price}
            for i, price in enumerate([100.0, 100.01, 100.02, 100.03, 101.0, 101.5])
        ]
    )


def test_sweep_parser_exposes_agent_mode_and_llm_overrides() -> None:
    help_text = build_parser().format_help()
    for flag in (
        "--agents",
        "--provider",
        "--model",
        "--temperature",
        "--max-tokens",
        "--timeout",
        "--base-url",
        "--api-key-env",
        "--audit-log",
        "--max-retries",
        "--retry-backoff",
        "--prompt-dir",
    ):
        assert flag in help_text


def test_build_simulator_wires_llm_agents_from_config() -> None:
    simulator = build_simulator(base_cfg(), agents="llm")

    assert isinstance(simulator.analyst, LLMAnalyst)
    assert isinstance(simulator.risk, LLMRiskManager)
    assert simulator.episodic_memory_depth == 5


def test_llm_sweep_falls_back_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("MISSING_TEST_OPENROUTER_KEY", raising=False)
    ohlcv = triggered_ohlcv()

    simulator = build_simulator(base_cfg(), agents="llm")
    pipeline_log, _trades, _vol_history = simulator.run(ohlcv)

    assert not pipeline_log.empty
    assert pipeline_log["agent_warnings"].str.contains("LLMAnalyst fallback").any()

    results = run_sweep(
        ohlcv,
        base_cfg(),
        {"llm.temperature": [0.0], "llm.max_tokens": [64]},
        max_runs=1,
        agents="llm",
    )

    assert len(results) == 1
    assert "alignment_score" in results.columns
    assert results.loc[0, "llm_temperature"] == 0.0
