from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime


class CalendarRepository(ABC):
    """
    Abstraction for event persistence and querying.
    SchedulingEngine depends on this; PostgreSQL is one concrete implementation.
    """

    @abstractmethod
    def create_event(
        self,
        user_id: str,
        title: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        priority: int,
        is_flexible: bool,
    ) -> dict:
        pass

    @abstractmethod
    def get_event(self, event_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def list_events(self, user_id: str, start: Optional[datetime], end: Optional[datetime]) -> list[dict]:
        pass

    @abstractmethod
    def update_event(self, event_id: str, **fields) -> dict:
        pass

    @abstractmethod
    def delete_event(self, event_id: str) -> None:
        pass

    @abstractmethod
    def get_flexible_slots(self, user_id: str, after: datetime, limit: int = 10) -> list[dict]:
        """Return upcoming flexible events that the scheduler may move."""
        pass

    @abstractmethod
    def find_overlapping_events(
        self,
        user_id: str,
        start: datetime,
        end: datetime,
        exclude_event_id: Optional[str] = None,
    ) -> list[dict]:
        """
        Return events for the user whose time range overlaps [start, end).

        Two intervals overlap iff existing.start < end AND existing.end > start
        (touching edges, where one ends exactly as the other begins, do NOT
        count as an overlap). Pass exclude_event_id to ignore a specific event
        — e.g. when checking whether an event can be moved onto its own slot.
        """
        pass

    @abstractmethod
    def create_proposal(
        self,
        user_id: str,
        topic_id: str,
        original_event_id: Optional[str],
        proposed_event_id: Optional[str],
        ai_reasoning: str,
    ) -> dict:
        pass

    @abstractmethod
    def get_proposal(self, proposal_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def list_proposals(self, user_id: str, status: Optional[str] = None) -> list[dict]:
        pass

    @abstractmethod
    def update_proposal_status(self, proposal_id: str, status: str, proposed_event_id: Optional[str] = None) -> dict:
        pass

    @abstractmethod
    def get_proposal_by_event_id(self, event_id: str) -> Optional[dict]:
        """Return the proposal whose proposed_event_id matches the given event."""
        pass
