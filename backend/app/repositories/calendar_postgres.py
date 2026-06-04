import logging
from datetime import datetime, timezone
from typing import Optional

from app.extensions import db
from app.interfaces.calendar_repository import CalendarRepository
from app.models import Event, ScheduleProposal
from app.time_utils import to_utc_naive

logger = logging.getLogger(__name__)


class PostgreSQLCalendarRepository(CalendarRepository):
    """Concrete CalendarRepository backed by PostgreSQL via SQLAlchemy."""

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
        event = Event(
            user_id=user_id,
            title=title,
            description=description,
            start_time=to_utc_naive(start_time),
            end_time=to_utc_naive(end_time),
            priority=priority,
            is_flexible=is_flexible,
        )
        db.session.add(event)
        db.session.commit()
        logger.info("Created event %s for user %s", event.id, user_id)
        return event.to_dict()

    def get_event(self, event_id: str) -> Optional[dict]:
        event = db.session.get(Event, event_id)
        return event.to_dict() if event else None

    def list_events(
        self, user_id: str, start: Optional[datetime], end: Optional[datetime]
    ) -> list[dict]:
        query = db.session.query(Event).filter_by(user_id=user_id)
        if start:
            query = query.filter(Event.start_time >= start)
        if end:
            query = query.filter(Event.end_time <= end)
        events = query.order_by(Event.start_time.asc()).all()
        return [e.to_dict() for e in events]

    def update_event(self, event_id: str, **fields) -> dict:
        event = db.session.get(Event, event_id)
        if not event:
            raise ValueError(f"Event {event_id} not found")
        allowed = {"title", "description", "start_time", "end_time", "priority", "is_flexible", "completed"}
        for key, value in fields.items():
            if key in allowed:
                if key in ("start_time", "end_time"):
                    value = to_utc_naive(value)
                setattr(event, key, value)
        db.session.commit()
        return event.to_dict()

    def delete_event(self, event_id: str) -> None:
        event = db.session.get(Event, event_id)
        if event:
            db.session.delete(event)
            db.session.commit()

    def get_flexible_slots(self, user_id: str, after: datetime, limit: int = 10) -> list[dict]:
        after = to_utc_naive(after)
        events = (
            db.session.query(Event)
            .filter(
                Event.user_id == user_id,
                Event.is_flexible == True,
                Event.start_time >= after,
            )
            .order_by(Event.priority.asc(), Event.start_time.asc())
            .limit(limit)
            .all()
        )
        return [e.to_dict() for e in events]

    def find_overlapping_events(
        self,
        user_id: str,
        start: datetime,
        end: datetime,
        exclude_event_id: Optional[str] = None,
    ) -> list[dict]:
        # Half-open overlap: existing.start < end AND existing.end > start.
        # Touching edges (existing.end == start, or existing.start == end) do not overlap.
        start, end = to_utc_naive(start), to_utc_naive(end)
        query = db.session.query(Event).filter(
            Event.user_id == user_id,
            Event.start_time < end,
            Event.end_time > start,
        )
        if exclude_event_id is not None:
            query = query.filter(Event.id != exclude_event_id)
        return [e.to_dict() for e in query.order_by(Event.start_time.asc()).all()]

    def create_proposal(
        self,
        user_id: str,
        topic_id: str,
        original_event_id: Optional[str],
        proposed_event_id: Optional[str],
        ai_reasoning: str,
    ) -> dict:
        proposal = ScheduleProposal(
            user_id=user_id,
            topic_id=topic_id,
            original_event_id=original_event_id,
            proposed_event_id=proposed_event_id,
            ai_reasoning=ai_reasoning,
        )
        db.session.add(proposal)
        db.session.commit()
        return proposal.to_dict()

    def get_proposal(self, proposal_id: str) -> Optional[dict]:
        proposal = db.session.get(ScheduleProposal, proposal_id)
        return proposal.to_dict() if proposal else None

    def list_proposals(self, user_id: str, status: Optional[str] = None) -> list[dict]:
        query = db.session.query(ScheduleProposal).filter_by(user_id=user_id)
        if status:
            query = query.filter_by(status=status)
        proposals = query.order_by(ScheduleProposal.created_at.desc()).all()
        return [p.to_dict() for p in proposals]

    def get_proposal_by_event_id(self, event_id: str) -> Optional[dict]:
        proposal = (
            db.session.query(ScheduleProposal)
            .filter(ScheduleProposal.proposed_event_id == event_id)
            .first()
        )
        return proposal.to_dict() if proposal else None

    def update_proposal_status(self, proposal_id: str, status: str, proposed_event_id: Optional[str] = None) -> dict:
        proposal = db.session.get(ScheduleProposal, proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        proposal.status = status
        if proposed_event_id:
            proposal.proposed_event_id = proposed_event_id
        db.session.commit()
        return proposal.to_dict()
