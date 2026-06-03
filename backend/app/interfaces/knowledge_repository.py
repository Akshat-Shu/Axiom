from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime


class KnowledgeRepository(ABC):
    """
    Abstraction for topic and relationship persistence.
    KnowledgeEngine depends on this; PostgreSQL is one concrete implementation.
    """

    @abstractmethod
    def create_topic(self, user_id: str, title: str, content_summary: str, file_key: Optional[str]) -> dict:
        pass

    @abstractmethod
    def get_topic(self, topic_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def list_topics(self, user_id: str) -> list[dict]:
        pass

    @abstractmethod
    def update_decay_score(self, topic_id: str, score: float) -> None:
        pass

    @abstractmethod
    def record_review(self, topic_id: str, user_id: str, duration_minutes: int) -> None:
        pass

    @abstractmethod
    def delete_topic(self, topic_id: str) -> None:
        pass

    @abstractmethod
    def create_relationship(self, source_id: str, target_id: str, rel_type: str, strength: float) -> dict:
        pass

    @abstractmethod
    def list_relationships(self, user_id: str) -> list[dict]:
        pass

    @abstractmethod
    def get_decaying_topics(self, user_id: str, threshold: float = 0.7) -> list[dict]:
        """Return topics whose decay_score exceeds the threshold, ordered descending."""
        pass
