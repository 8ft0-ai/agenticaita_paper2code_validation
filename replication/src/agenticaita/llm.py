"""Pluggable LLM provider interfaces for the replication harness.

The replication pipeline remains deterministic by default. This module provides
an explicit provider boundary for later LLM-backed agents while keeping network
calls isolated, auditable, and easy to mock in tests.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


class LLMError(RuntimeError):
    """Raised when an LLM provider cannot produce a valid JSON object."""


@dataclass(frozen=True)
class LLMConfig:
    """Runtime configuration for a chat-completion LLM provider."""

    provider: str = "openrouter"
    model: str = "qwen/qwen-2.5-7b-instruct"
    api_key_env: str = "OPENROUTER_API_KEY"
    temperature: float = 0.0
    max_tokens: int = 512
    base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    audit_log_path: str | None = None
    timeout_seconds: float = 60.0
    api_key: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> "LLMConfig":
        """Build configuration from either a root config or its ``llm`` section."""

        raw: Mapping[str, Any] = data or {}
        if "llm" in raw and isinstance(raw["llm"], Mapping):
            raw = raw["llm"]
        return cls(
            provider=str(raw.get("provider", cls.provider)).lower(),
            model=str(raw.get("model", cls.model)),
            api_key_env=str(raw.get("api_key_env", cls.api_key_env)),
            temperature=float(raw.get("temperature", cls.temperature)),
            max_tokens=int(raw.get("max_tokens", cls.max_tokens)),
            base_url=str(raw.get("base_url", cls.base_url)),
            audit_log_path=str(raw["audit_log_path"]) if raw.get("audit_log_path") else None,
            timeout_seconds=float(raw.get("timeout_seconds", cls.timeout_seconds)),
            api_key=str(raw["api_key"]) if raw.get("api_key") else None,
        )

    def resolved_api_key(self) -> str:
        """Return the configured API key without exposing it to audit logs."""

        key = self.api_key or os.environ.get(self.api_key_env, "")
        if not key:
            raise LLMError(f"Missing API key: set {self.api_key_env} or provide api_key in config")
        return key


class LLMProvider(ABC):
    """Abstract interface for synchronous JSON-producing LLM providers."""

    @abstractmethod
    def complete(self, system_prompt: str, user_message: str) -> dict[str, Any]:
        """Return a parsed JSON object from a provider completion."""


class OpenRouterProvider(LLMProvider):
    """OpenRouter implementation using the OpenAI-compatible chat endpoint."""

    def __init__(self, config: LLMConfig | Mapping[str, Any] | None = None) -> None:
        self.config = config if isinstance(config, LLMConfig) else LLMConfig.from_mapping(config)

    def complete(self, system_prompt: str, user_message: str) -> dict[str, Any]:
        api_key = self.config.resolved_api_key()
        request_payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.config.base_url,
            data=json.dumps(request_payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:  # noqa: S310 - URL is explicit provider config.
                raw_body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise LLMError(f"OpenRouter request failed: {exc}") from exc

        parsed = self._parse_chat_response(raw_body)
        self._audit(system_prompt, user_message, raw_body, parsed)
        return parsed

    def _parse_chat_response(self, raw_body: str) -> dict[str, Any]:
        try:
            payload = json.loads(raw_body)
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMError("OpenRouter response did not contain choices[0].message.content") from exc

        return parse_json_object(content)

    def _audit(self, system_prompt: str, user_message: str, raw_response: str, parsed_response: Mapping[str, Any]) -> None:
        if not self.config.audit_log_path:
            return
        path = Path(self.config.audit_log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": self.config.provider,
            "model": self.config.model,
            "system_prompt": system_prompt,
            "user_message": user_message,
            "raw_response": raw_response,
            "parsed_response": dict(parsed_response),
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.IGNORECASE | re.DOTALL)


def parse_json_object(content: Any) -> dict[str, Any]:
    """Parse a provider message content value into a JSON object."""

    if isinstance(content, Mapping):
        return dict(content)
    if not isinstance(content, str):
        raise LLMError("LLM content must be a JSON object or JSON string")

    text = content.strip()
    fenced = _JSON_FENCE_RE.match(text)
    if fenced:
        text = fenced.group(1).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError("LLM content was not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise LLMError("LLM content must parse to a JSON object")
    return parsed


def build_llm_provider(config: LLMConfig | Mapping[str, Any] | None) -> LLMProvider:
    """Create an LLM provider from config.

    The factory is intentionally small so future providers can be added without
    changing agent code. Unsupported providers fail fast rather than silently
    falling back to a different backend.
    """

    llm_config = config if isinstance(config, LLMConfig) else LLMConfig.from_mapping(config)
    if llm_config.provider == "openrouter":
        return OpenRouterProvider(llm_config)
    raise LLMError(f"Unsupported LLM provider: {llm_config.provider}")
