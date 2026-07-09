from pathlib import Path
from replicate import apply_llm_cli_overrides, build_parser, configured_prompts, configured_volatility_regime

def test_llm_cli_flags_and_overrides(tmp_path: Path) -> None:
    help_text = build_parser().format_help()
    for flag in ("--provider", "--model", "--temperature", "--max-tokens", "--timeout", "--base-url", "--api-key-env", "--audit-log", "--max-retries", "--retry-backoff", "--prompt-dir"):
        assert flag in help_text
    cfg = {"llm": {"model": "from-config"}}
    args = build_parser().parse_args(["--model", "qwen/custom", "--temperature", "0.4", "--max-retries", "3"])
    apply_llm_cli_overrides(cfg, args)
    assert cfg["llm"]["model"] == "qwen/custom" and cfg["llm"]["temperature"] == 0.4 and cfg["llm"]["max_retries"] == 3

def test_prompt_and_volatility_config(tmp_path: Path) -> None:
    cfg = {"agents": {"llm": {"prompts": {"analyst_system_prompt": "configured analyst"}, "volatility_regime": {"high_z_score": 5}}}}
    assert configured_prompts(cfg)["analyst_system_prompt"] == "configured analyst"
    (tmp_path / "risk_system_prompt.txt").write_text("file risk", encoding="utf-8")
    assert configured_prompts(cfg, tmp_path)["risk_system_prompt"] == "file risk"
    assert configured_volatility_regime(cfg).high_z_score == 5
