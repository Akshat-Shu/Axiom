"""
SchedulingEngine — high-level AI scheduling negotiation.

DIP: depends on LLMService, CalendarRepository, and KnowledgeRepository abstractions.
No concrete class is referenced here.
"""
import json
import logging
from datetime import datetime, timedelta, timezone

from app.interfaces.calendar_repository import CalendarRepository
from app.interfaces.knowledge_repository import KnowledgeRepository
from app.interfaces.llm import LLMService
from app.exceptions import EventConflictError

logger = logging.getLogger(__name__)

# Granularity and horizon used when searching for a free slot on the calendar.
_SLOT_SEARCH_STEP = timedelta(minutes=15)
_SLOT_SEARCH_HORIZON = timedelta(days=14)

CHAT_SYSTEM_PROMPT = """
You are an intelligent scheduling assistant helping a user schedule a knowledge review session.
You will be given the topic needing review, its decay score, the CURRENT TIME, and the user's current calendar.

STRICT RULES — the server ENFORCES these and will REJECT the whole proposal if you break them:
1. Every start_time and end_time you suggest MUST be strictly AFTER the current time. Never suggest a time in the past.
2. end_time must always be after start_time.
3. Only propose moving events that have is_flexible=true. Moving a non-flexible event is rejected.
4. All timestamps must be ISO 8601 with UTC offset, e.g. "2026-06-04T14:00:00+00:00".
5. Prefer scheduling at least 1 hour from now to give the user time to prepare.
6. NO OVERLAPS. A created or moved event must not overlap any existing event in the calendar shown below.
   If the user's preferred slot is busy, either pick a free slot or move the conflicting event (only if it is flexible) to a free slot in the SAME proposal.

Have a natural conversation to find the best review slot. You can propose to:
- Create a new review session at a specific future time
- Move a flexible existing event to make room
- Change the priority of an existing event

Always respond with valid JSON in exactly this structure:
{
  "message": "your conversational reply to the user",
  "proposed_changes": [
    {"type": "create_event", "title": "string", "start_time": "ISO8601+offset", "end_time": "ISO8601+offset", "priority": 1, "description": "string"},
    {"type": "move_event", "event_id": "string", "event_title": "string", "new_start_time": "ISO8601+offset", "new_end_time": "ISO8601+offset"},
    {"type": "update_priority", "event_id": "string", "event_title": "string", "new_priority": integer}
  ]
}
IMPORTANT: On your FIRST response you MUST include at least one concrete proposed_change (a create_event at a specific future time). Never reply with only a question on the first turn — always lead with a concrete suggestion the user can see immediately, then invite them to adjust it.
""".strip()

SCHEDULING_SYSTEM_PROMPT = """
You are an intelligent academic scheduling assistant for Axiom.
You help users protect time for critical knowledge review by analysing their calendar.

Given a decaying topic and a list of upcoming flexible calendar events, propose ONE review session.
Always set can_schedule: true — even if there are no flexible events to move, still propose a
review session at a sensible time (e.g. tomorrow morning). Only set event_to_move_id if there is
a flexible event worth rescheduling to make room.

Return ONLY valid JSON in this exact format:
{
  "can_schedule": true,
  "event_to_move_id": "string or null — ID of a flexible event to reschedule, or null",
  "review_title": "string — title for the new review session",
  "review_duration_minutes": integer,
  "suggested_new_time_for_moved_event": "ISO 8601 string or null",
  "reasoning": "string — conversational explanation for the user (2-3 sentences)"
}
""".strip()


class SchedulingEngine:
    def __init__(
        self,
        llm: LLMService,
        calendar_repo: CalendarRepository,
        knowledge_repo: KnowledgeRepository,
    ):
        self._llm = llm
        self._calendar_repo = calendar_repo
        self._knowledge_repo = knowledge_repo

    def generate_proposals(self, user_id: str, decay_threshold: float = 0.3) -> list[dict]:
        """
        Identify critically decaying topics, query flexible calendar slots,
        and use the LLM to generate schedule proposals.
        Returns a list of created proposal dicts.
        """
        critical_topics = self._knowledge_repo.get_decaying_topics(user_id, threshold=decay_threshold)
        if not critical_topics:
            logger.info("No critically decaying topics for user %s", user_id)
            return []

        existing_pending = {p["topic_id"] for p in self._calendar_repo.list_proposals(user_id, status="pending")}
        eligible_topics = [t for t in critical_topics if t["id"] not in existing_pending]

        if not eligible_topics:
            logger.info("All decaying topics already have pending proposals for user %s", user_id)
            return []

        now = datetime.now(timezone.utc)
        flexible_slots = self._calendar_repo.get_flexible_slots(user_id, after=now, limit=10)

        proposals = []
        next_slot_start = now + timedelta(hours=1)
        for topic in eligible_topics[:3]:
            proposal = self._negotiate_slot(user_id, topic, flexible_slots, start_after=next_slot_start)
            if proposal:
                proposals.append(proposal)
                duration = proposal.get("review_duration_minutes") or 60
                next_slot_start = next_slot_start + timedelta(minutes=duration + 15)

        return proposals

    def accept_proposal(self, proposal_id: str, duration_minutes: int = 60) -> dict:
        """
        Create the review session event and mark the proposal accepted.

        The review is always placed in a slot that does NOT overlap any existing
        event. If the proposal nominated a flexible event to move out of the way
        (original_event_id), that event is honoured: it is relocated to the next
        free slot so the review can take its place.
        """
        proposal = self._calendar_repo.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        if proposal["status"] != "pending":
            raise ValueError(f"Proposal {proposal_id} is not in pending state")

        topic = self._knowledge_repo.get_topic(proposal["topic_id"])
        title = f"Review: {topic['title']}" if topic else "Review Session"
        user_id = proposal["user_id"]

        now = datetime.now(timezone.utc)
        earliest = now + timedelta(hours=1)
        review_delta = timedelta(minutes=duration_minutes)

        # Honour a proposed move: if a flexible event was nominated and it sits in
        # the way of our intended slot, relocate it first so the review can land.
        move_id = proposal.get("original_event_id")
        if move_id:
            mover = self._calendar_repo.get_event(move_id)
            if mover and mover.get("is_flexible"):
                intended_end = earliest + review_delta
                if self._calendar_repo.find_overlapping_events(user_id, earliest, intended_end, exclude_event_id=move_id) == [] \
                        and self._overlaps(user_id, earliest, intended_end):
                    # The only thing blocking the intended slot is the nominated event → move it.
                    m_start = self._parse_iso(mover["start_time"])
                    m_end = self._parse_iso(mover["end_time"])
                    m_duration = m_end - m_start
                    new_start, new_end = self._find_free_slot(user_id, m_duration, intended_end, exclude_event_id=move_id)
                    self._calendar_repo.update_event(move_id, start_time=new_start, end_time=new_end)
                    logger.info("Honoured proposed move: relocated flexible event %s to %s", move_id, new_start.isoformat())

        review_start, review_end = self._find_free_slot(user_id, review_delta, earliest)
        review_event = self._calendar_repo.create_event(
            user_id=user_id,
            title=title,
            description=f"Axiom review session accepted from proposal {proposal_id}",
            start_time=review_start,
            end_time=review_end,
            priority=1,
            is_flexible=False,
        )

        updated = self._calendar_repo.update_proposal_status(proposal_id, "accepted", proposed_event_id=review_event["id"])
        logger.info("Accepted proposal %s, created event %s at %s", proposal_id, review_event["id"], review_start.isoformat())
        return updated

    def decline_proposal(self, proposal_id: str) -> dict:
        """Mark a proposal as declined without modifying the calendar."""
        proposal = self._calendar_repo.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        updated = self._calendar_repo.update_proposal_status(proposal_id, "declined")
        logger.info("Declined proposal %s", proposal_id)
        return updated

    def _negotiate_slot(self, user_id: str, topic: dict, flexible_slots: list[dict], start_after: datetime | None = None) -> dict | None:
        user_message = (
            f"Topic needing review:\n"
            f"  Title: {topic['title']}\n"
            f"  Decay score: {topic['decay_score']:.2f} (1.0 = fully forgotten)\n"
            f"  Last reviewed: {topic.get('last_reviewed_at', 'Never')}\n\n"
            f"Upcoming flexible calendar events (may be moved):\n"
            + json.dumps(flexible_slots, indent=2, default=str)
        )

        try:
            raw = self._llm.complete(
                system_prompt=SCHEDULING_SYSTEM_PROMPT,
                user_message=user_message,
                json_mode=True,
            )
            suggestion = json.loads(raw)
        except Exception as exc:
            logger.error("LLM scheduling failed for topic %s: %s", topic["id"], exc)
            return None

        now = datetime.now(timezone.utc)
        slot_start = start_after if start_after else now + timedelta(hours=1)

        if not suggestion.get("can_schedule"):
            suggestion = {
                "can_schedule": True,
                "event_to_move_id": None,
                "review_title": f"Review: {topic['title']}",
                "review_duration_minutes": 60,
                "suggested_new_time_for_moved_event": None,
                "reasoning": f"'{topic['title']}' has decayed significantly and needs review. A 60-minute session has been scheduled.",
            }
        duration_mins = int(suggestion.get("review_duration_minutes", 60))

        proposal = self._calendar_repo.create_proposal(
            user_id=user_id,
            topic_id=topic["id"],
            original_event_id=suggestion.get("event_to_move_id"),
            proposed_event_id=None,
            ai_reasoning=suggestion.get("reasoning", ""),
        )
        return {**proposal, "review_duration_minutes": duration_mins, "_review_title": suggestion.get("review_title", f"Review: {topic['title']}"), "_slot_start": slot_start}

    def chat_about_proposal(self, proposal_id: str, messages: list[dict], user_message: str, client_now: str | None = None, tz_name: str = "UTC", utc_offset_minutes: int = 0) -> dict:
        """Multi-turn conversation to collaboratively build a schedule change."""
        proposal = self._calendar_repo.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        topic = self._knowledge_repo.get_topic(proposal["topic_id"])
        now_utc = datetime.now(timezone.utc)
        if client_now:
            try:
                now_utc = datetime.fromisoformat(client_now).replace(tzinfo=timezone.utc) if datetime.fromisoformat(client_now).tzinfo is None else datetime.fromisoformat(client_now)
            except ValueError:
                pass

        # Express offset as ±HH:MM string for ISO 8601
        offset_sign = "+" if utc_offset_minutes >= 0 else "-"
        abs_offset = abs(utc_offset_minutes)
        offset_str = f"{offset_sign}{abs_offset // 60:02d}:{abs_offset % 60:02d}"

        # Local time = UTC + offset
        local_now = now_utc + timedelta(minutes=utc_offset_minutes)
        local_earliest = local_now + timedelta(hours=1)

        all_events = self._calendar_repo.list_events(proposal["user_id"], start=None, end=None)
        future_events = [e for e in all_events if e["start_time"] > now_utc.strftime("%Y-%m-%dT%H:%M:%S")]

        system_content = CHAT_SYSTEM_PROMPT + f"""

## Time context
- User timezone: {tz_name} (UTC{offset_str})
- Current local time: {local_now.strftime("%Y-%m-%dT%H:%M:%S")}{offset_str}
- Current UTC time:   {now_utc.strftime("%Y-%m-%dT%H:%M:%S+00:00")}
- Earliest valid start (local): {local_earliest.strftime("%Y-%m-%dT%H:%M:%S")}{offset_str}

IMPORTANT: All times in proposed_changes MUST use the offset "{offset_str}" so the user's calendar shows the correct local time. For example, if you mean 9:20 AM local, write "...T09:20:00{offset_str}". Never use +00:00 unless the user is in UTC.

## Topic to review
- Title: {topic['title']}
- Decay: {topic['decay_score']:.0%} forgotten
- Last reviewed: {topic.get('last_reviewed_at') or 'Never'}

## Upcoming calendar events (future only)
{json.dumps(future_events, indent=2, default=str)}
"""
        full_messages = [{"role": "system", "content": system_content}]
        full_messages.extend(messages)
        if user_message:
            full_messages.append({"role": "user", "content": user_message})
        elif not messages:
            full_messages.append({"role": "user", "content": f"I need to schedule a review session for '{topic['title']}'. My local time is {local_now.strftime('%I:%M %p')} ({tz_name}). What do you suggest?"})

        raw = self._llm.complete_messages(full_messages, json_mode=True)
        return json.loads(raw)

    def apply_proposal_changes(self, proposal_id: str, changes: list[dict]) -> dict:
        """
        Apply the agreed calendar changes and mark the proposal accepted.

        Robustness guarantees (all enforced server-side, not just in the prompt):
          * Every change is structurally validated BEFORE anything is mutated.
          * move_event is rejected unless the target exists, belongs to the user,
            and is flexible (is_flexible=True).
          * No create or move may land on a slot that overlaps another event —
            an EventConflictError is raised instead of silently double-booking.
          * Failures are propagated, never swallowed. Moves are applied before
            creates so a "move X out of the way, then book the freed slot" plan
            still works.
        """
        proposal = self._calendar_repo.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        if proposal["status"] != "pending":
            raise ValueError(f"Proposal {proposal_id} is not pending")

        user_id = proposal["user_id"]
        now = datetime.now(timezone.utc)

        creates: list[tuple[dict, datetime, datetime]] = []
        moves: list[tuple[str, datetime, datetime]] = []
        priorities: list[tuple[str, int]] = []

        # ---- Phase 1: structural validation only (no DB mutations yet) ----
        for change in changes:
            t = change.get("type")
            if t == "create_event":
                start = self._parse_iso(change["start_time"])
                end = self._parse_iso(change["end_time"])
                if start <= now:
                    raise EventConflictError(f"Cannot create event in the past: {change['start_time']}")
                if end <= start:
                    raise EventConflictError("Event end_time must be after start_time")
                creates.append((change, start, end))
            elif t == "move_event":
                event_id = change.get("event_id")
                target = self._calendar_repo.get_event(event_id) if event_id else None
                if not target:
                    raise EventConflictError(f"Cannot move unknown event: {event_id}")
                if target["user_id"] != user_id:
                    raise EventConflictError(f"Event {event_id} does not belong to this user")
                if not target.get("is_flexible"):
                    raise EventConflictError(f"Cannot move '{target['title']}' — it is not flexible.")
                new_start = self._parse_iso(change["new_start_time"])
                new_end = self._parse_iso(change["new_end_time"])
                if new_start <= now:
                    raise EventConflictError(f"Cannot move event to the past: {change['new_start_time']}")
                if new_end <= new_start:
                    raise EventConflictError("Moved event end_time must be after start_time")
                moves.append((event_id, new_start, new_end))
            elif t == "update_priority":
                event_id = change.get("event_id")
                target = self._calendar_repo.get_event(event_id) if event_id else None
                if not target:
                    raise EventConflictError(f"Cannot update unknown event: {event_id}")
                if target["user_id"] != user_id:
                    raise EventConflictError(f"Event {event_id} does not belong to this user")
                try:
                    pr = int(change["new_priority"])
                except (KeyError, TypeError, ValueError):
                    raise EventConflictError("new_priority must be an integer between 1 and 5")
                if not 1 <= pr <= 5:
                    raise EventConflictError("new_priority must be between 1 and 5")
                priorities.append((event_id, pr))
            else:
                logger.warning("Ignoring unknown change type: %s", t)

        # ---- Phase 2: apply moves (free up space) and priority changes ----
        for event_id, new_start, new_end in moves:
            conflicts = self._calendar_repo.find_overlapping_events(user_id, new_start, new_end, exclude_event_id=event_id)
            if conflicts:
                raise EventConflictError(
                    f"Cannot move event to {new_start.isoformat()} — it overlaps "
                    f"{len(conflicts)} existing event(s).",
                    conflicts=conflicts,
                )
            self._calendar_repo.update_event(event_id, start_time=new_start, end_time=new_end)

        for event_id, pr in priorities:
            self._calendar_repo.update_event(event_id, priority=pr)

        # ---- Phase 3: create new events into now-confirmed-free slots ----
        created_event_id = None
        for change, start, end in creates:
            conflicts = self._calendar_repo.find_overlapping_events(user_id, start, end)
            if conflicts:
                raise EventConflictError(
                    f"Cannot create '{change.get('title')}' at {start.isoformat()} — it overlaps "
                    f"{len(conflicts)} existing event(s).",
                    conflicts=conflicts,
                )
            event = self._calendar_repo.create_event(
                user_id=user_id,
                title=change["title"],
                description=change.get("description", "Axiom review session"),
                start_time=start,
                end_time=end,
                priority=change.get("priority", 1),
                is_flexible=False,
            )
            if created_event_id is None:
                created_event_id = event["id"]

        return self._calendar_repo.update_proposal_status(proposal_id, "accepted", proposed_event_id=created_event_id)

    # ------------------------------------------------------------------ #
    # Scheduling helpers (overlap-aware, depend only on the repo abstraction)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _parse_iso(value: str) -> datetime:
        """Parse an ISO 8601 string into a timezone-aware UTC-anchored datetime."""
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def _overlaps(self, user_id: str, start: datetime, end: datetime, exclude_event_id: str | None = None) -> bool:
        return bool(self._calendar_repo.find_overlapping_events(user_id, start, end, exclude_event_id=exclude_event_id))

    def _find_free_slot(
        self,
        user_id: str,
        duration: timedelta,
        earliest: datetime,
        exclude_event_id: str | None = None,
    ) -> tuple[datetime, datetime]:
        """
        Scan forward from `earliest` in fixed steps for the first window of length
        `duration` that overlaps no existing event. Falls back to the far end of the
        search horizon rather than failing if the calendar is somehow fully booked.
        """
        slot_start = earliest
        deadline = earliest + _SLOT_SEARCH_HORIZON
        while slot_start < deadline:
            slot_end = slot_start + duration
            if not self._overlaps(user_id, slot_start, slot_end, exclude_event_id=exclude_event_id):
                return slot_start, slot_end
            slot_start += _SLOT_SEARCH_STEP
        logger.warning("No free slot within %s for user %s; placing at horizon end", _SLOT_SEARCH_HORIZON, user_id)
        return deadline, deadline + duration
