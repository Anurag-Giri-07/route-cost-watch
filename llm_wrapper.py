"""Provider-agnostic, cached and logged LLM access."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv
from openai import OpenAI

from config import (
    LLM_API_KEY_ENV_VAR,
    LLM_BASE_URL,
    LLM_CACHE_DIR,
    LLM_DEFAULT_MODEL,
    LLM_MAX_OUTPUT_TOKENS,
    LLM_TEMPERATURE,
    LLM_USAGE_LOG_PATH,
)

USAGE_LOG_COLUMNS = [
    "timestamp_utc",
    "purpose",
    "model",
    "prompt_hash",
    "input_tokens",
    "output_tokens",
    "cache_hit",
]


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int
    output_tokens: int


class ChatClient(Protocol):
    def complete(self, model: str, prompt: str) -> LLMResponse: ...


class OpenAICompatibleClient:
    """Adapter for Groq and other OpenAI-compatible chat APIs."""

    def __init__(self, api_key: str, base_url: str) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def complete(self, model: str, prompt: str) -> LLMResponse:
        response = self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_OUTPUT_TOKENS,
        )
        usage = response.usage
        return LLMResponse(
            content=response.choices[0].message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )

    def list_model_ids(self) -> list[str]:
        """Return model IDs visible to this API key."""
        return sorted(model.id for model in self._client.models.list().data)


class LLMWrapper:
    """Use one path for all LLM calls, with prompt-hash caching and logging."""

    def __init__(
        self,
        client: ChatClient,
        model: str,
        cache_dir: Path = LLM_CACHE_DIR,
        usage_log_path: Path = LLM_USAGE_LOG_PATH,
    ) -> None:
        self.client = client
        self.model = model
        self.cache_dir = cache_dir
        self.usage_log_path = usage_log_path

    def complete(self, purpose: str, prompt: str) -> str:
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        cache_path = self.cache_dir / f"{prompt_hash}.json"
        if cache_path.exists():
            with cache_path.open(encoding="utf-8") as cache_file:
                cached = LLMResponse(**json.load(cache_file))
            self._log_usage(purpose, prompt_hash, cached, cache_hit=True)
            return cached.content

        response = self.client.complete(self.model, prompt)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with cache_path.open("w", encoding="utf-8") as cache_file:
            json.dump(asdict(response), cache_file)
        self._log_usage(purpose, prompt_hash, response, cache_hit=False)
        return response.content

    def _log_usage(
        self, purpose: str, prompt_hash: str, response: LLMResponse, cache_hit: bool
    ) -> None:
        self.usage_log_path.parent.mkdir(parents=True, exist_ok=True)
        needs_header = not self.usage_log_path.exists()
        with self.usage_log_path.open("a", newline="", encoding="utf-8") as log_file:
            writer = csv.DictWriter(log_file, fieldnames=USAGE_LOG_COLUMNS)
            if needs_header:
                writer.writeheader()
            writer.writerow(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "purpose": purpose,
                    "model": self.model,
                    "prompt_hash": prompt_hash,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cache_hit": "Yes" if cache_hit else "No",
                }
            )


def create_default_wrapper(
    cache_dir: Path = LLM_CACHE_DIR,
    usage_log_path: Path = LLM_USAGE_LOG_PATH,
) -> LLMWrapper:
    """Create the configured API client without exposing the secret in code."""
    load_dotenv()
    api_key = os.getenv(LLM_API_KEY_ENV_VAR)
    if not api_key:
        raise RuntimeError(f"{LLM_API_KEY_ENV_VAR} is required for LLM explanations")
    model = os.getenv("LLM_MODEL", LLM_DEFAULT_MODEL)
    return LLMWrapper(
        OpenAICompatibleClient(api_key, LLM_BASE_URL),
        model,
        cache_dir,
        usage_log_path,
    )


def list_configured_model_ids() -> list[str]:
    """List models available to the configured API key without a chat call."""
    load_dotenv()
    api_key = os.getenv(LLM_API_KEY_ENV_VAR)
    if not api_key:
        raise RuntimeError(f"{LLM_API_KEY_ENV_VAR} is required to list models")
    return OpenAICompatibleClient(api_key, LLM_BASE_URL).list_model_ids()
