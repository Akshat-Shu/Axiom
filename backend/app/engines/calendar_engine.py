"""
CalendarEngine — high-level orchestration for manual calendar mutations.

DIP: depends only on the CalendarRepository abstraction. No concrete class
(PostgreSQL, SQLAlchemy) is referenced here. This is the single place that
owns the "events must not overlap" business rule for user-driven create/update,
so controllers stay thin and the rule cannot be bypassed or duplicated.
"""
import logging
from datetime import datetime, timezone

from app.interfaces.calendar_repository import CalendarRepository
from app.exceptions import EventConflictError

logger = logging.getLogger(__name__)


def _naive(dt: datetime) -> datetime:
    """Drop tzinfo so naive (SQLite) and aware datetimes compare safely."""
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


class CalendarEngine:
    def __init__(self, repo: CalendarRepository):
        self._repo = repo

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
        """
        Create an event, rejecting it if it overlaps any existing event for the
        user. Raises EventConflictError (carrying the conflicts) instead of
        creating a double-booking.
        """
        conflicts = self._repo.find_overlapping_events(user_id, start_time, end_time)
        if conflicts:
            raise EventConflictError(
                f"'{title}' overlaps {len(conflicts)} existing event(s).",
                conflicts=conflicts,
            )
        return self._repo.create_event(
            user_id=user_id,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            priority=priority,
            is_flexible=is_flexible,
        )

    def update_event(self, event_id: str, **fields) -> dict:
        """
        Update an event. If the time window changes, reject the update when the
        new window overlaps any OTHER event for the user.
        """
        existing = self._repo.get_event(event_id)
        if not existing:
            raise ValueError(f"Event {event_id} not found")

        if "start_time" in fields or "end_time" in fields:
            new_start = fields.get("start_time") or datetime.fromisoformat(existing["start_time"])
            new_end = fields.get("end_time") or datetime.fromisoformat(existing["end_time"])
            if _naive(new_end) <= _naive(new_start):
                raise EventConflictError("end_time must be after start_time")
            conflicts = self._repo.find_overlapping_events(
                existing["user_id"], new_start, new_end, exclude_event_id=event_id
            )
            if conflicts:
                raise EventConflictError(
                    f"Updated time window overlaps {len(conflicts)} existing event(s).",
                    conflicts=conflicts,
                )

        return self._repo.update_event(event_id, **fields)
