from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Protocol


class LLMProvider(Protocol):
    """Minimal provider-independent text generation interface."""

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 256,
        temperature: float = 0.0,
    ) -> str:
        ...


class OpenAICompatibleLLM:
    """Minimal client for OpenAI-compatible chat endpoints."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        if not base_url:
            raise ValueError(
                "base_url cannot be empty."
            )

        if not api_key:
            raise ValueError(
                "api_key cannot be empty."
            )

        if not model:
            raise ValueError(
                "model cannot be empty."
            )

        self.base_url = (
            base_url.rstrip("/")
        )

        self.api_key = api_key
        self.model = model
        self.timeout_seconds = (
            timeout_seconds
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 256,
        temperature: float = 0.0,
    ) -> str:

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        system_prompt
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        user_prompt
                    ),
                },
            ],
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        request = urllib.request.Request(
            (
                f"{self.base_url}"
                "/chat/completions"
            ),
            data=json.dumps(
                payload
            ).encode("utf-8"),
            headers={
                "Authorization": (
                    f"Bearer "
                    f"{self.api_key}"
                ),
                "Content-Type": (
                    "application/json"
                ),
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=(
                    self.timeout_seconds
                ),
            ) as response:
                body = json.loads(
                    response.read().decode(
                        "utf-8"
                    )
                )

        except urllib.error.HTTPError as exc:
            error_body = (
                exc.read()
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

            raise RuntimeError(
                "LLM request failed with "
                f"HTTP {exc.code}: "
                f"{error_body}"
            ) from exc

        try:
            return (
                body["choices"][0]
                ["message"]["content"]
            )

        except (
            KeyError,
            IndexError,
            TypeError,
        ) as exc:
            raise RuntimeError(
                "Unexpected LLM response "
                f"format: {body}"
            ) from exc