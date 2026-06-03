from abc import ABC, abstractmethod
from typing import Any


class LLMService(ABC):
    """
    Abstraction for LLM text-generation.
    High-level modules (KnowledgeEngine, SchedulingEngine) depend on this,
    never on OpenRouter or any specific provider directly.
    """

    @abstractmethod
    def complete(self, system_prompt: str, user_message: str, json_mode: bool = False) -> str:
        """Single-turn completion. When json_mode=True the response is guaranteed to be valid JSON."""

    @abstractmethod
    def complete_messages(self, messages: list[dict], json_mode: bool = False) -> str:
        """Multi-turn completion. messages: [{role, content}, ...] including system message."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the provider is reachable and the API key is valid."""
