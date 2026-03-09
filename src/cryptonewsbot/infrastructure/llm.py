from __future__ import annotations

import json
from typing import Dict
from urllib.request import Request, urlopen

from cryptonewsbot.config import AppConfig


class LLMRewriter:
    def __init__(self, config: AppConfig) -> None:
        self._provider = config.llm_provider
        self._api_key = config.llm_api_key
        self._model = config.llm_model
        self._base_url = config.llm_base_url

    @property
    def enabled(self) -> bool:
        return self._provider in {"openai", "gemini"} and bool(self._api_key and self._model)

    def rewrite(self, system_prompt: str, user_prompt: str) -> Dict[str, str]:
        if not self.enabled:
            raise ValueError("LLM rewriter is not configured.")
        if self._provider == "gemini":
            return self._rewrite_with_gemini(system_prompt, user_prompt)
        return self._rewrite_with_openai(system_prompt, user_prompt)

    def _rewrite_with_openai(self, system_prompt: str, user_prompt: str) -> Dict[str, str]:
        payload = json.dumps(
            {
                "model": self._model,
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
        ).encode("utf-8")
        request = Request(
            self._base_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
                "User-Agent": "cryptonewsbot/0.1",
            },
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        return _parse_json_object(body["choices"][0]["message"]["content"])

    def _rewrite_with_gemini(self, system_prompt: str, user_prompt: str) -> Dict[str, str]:
        base_url = self._base_url.rstrip("/")
        endpoint = f"{base_url}/{self._model}:generateContent"
        payload = json.dumps(
            {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "responseMimeType": "application/json",
                    "responseSchema": {
                        "type": "OBJECT",
                        "properties": {
                            "headline": {"type": "STRING"},
                            "body": {"type": "STRING"},
                        },
                        "required": ["headline", "body"],
                        "propertyOrdering": ["headline", "body"],
                    },
                },
            }
        ).encode("utf-8")
        request = Request(
            endpoint,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": str(self._api_key),
                "User-Agent": "cryptonewsbot/0.1",
            },
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        parts = body["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts)
        return _parse_json_object(text)


def _parse_json_object(content: str) -> Dict[str, str]:
    parsed = json.loads(content)
    return {
        "headline": str(parsed.get("headline", "")).strip(),
        "body": str(parsed.get("body", "")).strip(),
        "telegram_body": str(parsed.get("telegram_body", parsed.get("body", ""))).strip(),
    }
