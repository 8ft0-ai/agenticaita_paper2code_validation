from __future__ import annotations

import json
import urllib.error
from pathlib import Path

import pytest

from src.agenticaita.llm import LLMConfig, LLMError, OpenRouterProvider, build_llm_provider, parse_json_object


class FakeHTTPResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


RESPONSE_PAYLOAD = {"choices": [{"message": {"content": '{"approved": true, "size_usd": 100, "negotiation_summary": "ok"}'}}]}


def http_error(status: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://openrouter.ai/api/v1/chat/completions", status, f"status {status}", {}, None)


def test_openrouter_provider_parses_json_response_and_writes_audit_log(monkeypatch, tmp_path: Path) -> None:
    captured: dict = {}
    response_payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "signal": "long",
                            "confidence": 0.72,
                            "entry_price": 100.0,
                            "stop_loss": 99.0,
                            "take_profit": 103.0,
                            "size_usd": 188.0,
                            "reasoning": "Composite score and orderbook context support a long.",
                        }
                    )
                }
            }
        ]
    }

    def fake_urlopen(request, timeout):  # noqa: ANN001
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeHTTPResponse(response_payload)

    monkeypatch.setenv("OPENROUTER_API_KEY", "secret-test-key")
    monkeypatch.setattr("src.agenticaita.llm.urllib.request.urlopen", fake_urlopen)
    audit_path = tmp_path / "llm_audit.jsonl"
    provider = OpenRouterProvider(
        {
            "model": "qwen/test-model",
            "temperature": 0.0,
            "max_tokens": 256,
            "audit_log_path": str(audit_path),
            "timeout_seconds": 12,
        }
    )

    result = provider.complete("system prompt", "user message")

    assert result["signal"] == "long"
    assert result["confidence"] == 0.72
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer secret-test-key"
    assert captured["payload"]["model"] == "qwen/test-model"
    assert captured["payload"]["messages"][0] == {"role": "system", "content": "system prompt"}
    assert captured["payload"]["messages"][1] == {"role": "user", "content": "user message"}
    assert captured["payload"]["max_tokens"] == 256
    assert captured["timeout"] == 12

    audit_text = audit_path.read_text(encoding="utf-8")
    assert "system prompt" in audit_text
    assert "user message" in audit_text
    assert "secret-test-key" not in audit_text


def test_openrouter_provider_reads_api_key_from_config_when_env_missing(monkeypatch) -> None:
    captured: dict = {}

    def fake_urlopen(request, timeout):  # noqa: ANN001, ARG001
        captured["headers"] = dict(request.header_items())
        return FakeHTTPResponse({"choices": [{"message": {"content": '{"approved": true, "size_usd": 100, "negotiation_summary": "ok"}'}}]})

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("src.agenticaita.llm.urllib.request.urlopen", fake_urlopen)

    provider = OpenRouterProvider(LLMConfig(api_key="config-key"))
    result = provider.complete("system", "user")

    assert result["approved"] is True
    assert captured["headers"]["Authorization"] == "Bearer config-key"


def test_openrouter_provider_raises_when_api_key_missing(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    provider = OpenRouterProvider({"api_key_env": "OPENROUTER_API_KEY"})

    with pytest.raises(LLMError, match="Missing API key"):
        provider.complete("system", "user")


@pytest.mark.parametrize("status", [429, 503])
def test_openrouter_provider_retries_transient_http_errors(monkeypatch, status: int) -> None:
    calls = []

    def fake_urlopen(request, timeout):  # noqa: ANN001, ARG001
        calls.append(request)
        if len(calls) == 1:
            raise http_error(status)
        return FakeHTTPResponse(RESPONSE_PAYLOAD)

    monkeypatch.setattr("src.agenticaita.llm.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("src.agenticaita.llm.time.sleep", lambda _seconds: None)

    provider = OpenRouterProvider(LLMConfig(api_key="config-key", max_retries=1, retry_backoff_seconds=0))
    assert provider.complete("system", "user")["approved"] is True
    assert len(calls) == 2


@pytest.mark.parametrize("status", [401, 403])
def test_openrouter_provider_does_not_retry_permanent_http_errors(monkeypatch, status: int) -> None:
    calls = []

    def fake_urlopen(request, timeout):  # noqa: ANN001, ARG001
        calls.append(request)
        raise http_error(status)

    monkeypatch.setattr("src.agenticaita.llm.urllib.request.urlopen", fake_urlopen)

    provider = OpenRouterProvider(LLMConfig(api_key="config-key", max_retries=2, retry_backoff_seconds=0))
    with pytest.raises(LLMError, match=f"permanent HTTP error {status}"):
        provider.complete("system", "user")
    assert len(calls) == 1


def test_parse_json_object_accepts_fenced_json_and_rejects_non_object() -> None:
    assert parse_json_object('```json\n{"signal": "wait", "confidence": 0.1}\n```') == {"signal": "wait", "confidence": 0.1}

    with pytest.raises(LLMError, match="JSON object"):
        parse_json_object('["not", "an", "object"]')


def test_build_llm_provider_from_root_config() -> None:
    provider = build_llm_provider(
        {
            "llm": {
                "provider": "openrouter",
                "model": "qwen/custom",
                "api_key_env": "CUSTOM_OPENROUTER_KEY",
            }
        }
    )

    assert isinstance(provider, OpenRouterProvider)
    assert provider.config.model == "qwen/custom"
    assert provider.config.api_key_env == "CUSTOM_OPENROUTER_KEY"
