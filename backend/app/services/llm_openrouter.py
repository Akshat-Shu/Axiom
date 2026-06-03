import json
import logging
import time
from typing import Any

import httpx

from app.interfaces.llm import LLMService

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds


class OpenRouterLLMService(LLMService):
    """
    Concrete LLMService backed by OpenRouter.
    Paste your key into OPENROUTER_API_KEY in the .env file.
    """

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, timeout: int = 60):
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY must not be empty")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://axiom-app.local",
            "X-Title": "Axiom",
        }

    def _call(self, messages: list[dict], json_mode: bool = False) -> str:
        payload: dict[str, Any] = {"model": self._model, "messages": messages}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(
                        f"{OPENROUTER_BASE_URL}/chat/completions",
                        headers=self._headers,
                        json=payload,
                    )
                if response.status_code == 429:
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning("Rate limited (attempt %d/%d). Retrying in %ds.", attempt, MAX_RETRIES, wait)
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                logger.debug("LLM OK (model=%s, tokens=%s)", self._model, result.get("usage"))
                return content
            except httpx.HTTPStatusError as exc:
                logger.error("OpenRouter HTTP error (attempt %d): %s", attempt, exc)
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(RETRY_BACKOFF_BASE ** attempt)
            except httpx.RequestError as exc:
                logger.error("OpenRouter request error (attempt %d): %s", attempt, exc)
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(RETRY_BACKOFF_BASE ** attempt)
        raise RuntimeError("OpenRouter LLM call failed after all retries")

    def complete(self, system_prompt: str, user_message: str, json_mode: bool = False) -> str:
        return self._call(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
            json_mode=json_mode,
        )

    def complete_messages(self, messages: list[dict], json_mode: bool = False) -> str:
        return self._call(messages, json_mode=json_mode)

    def health_check(self) -> bool:
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(
                    f"{OPENROUTER_BASE_URL}/models",
                    headers=self._headers,
                )
            return response.status_code == 200
        except Exception as exc:
            logger.warning("OpenRouter health check failed: %s", exc)
            return False
