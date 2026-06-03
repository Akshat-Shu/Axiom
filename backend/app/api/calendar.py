import logging
from flask import Blueprint, request, jsonify, current_app
from marshmallow import ValidationError

from app.schemas.event_schema import EventCreateSchema, EventUpdateSchema, EventListQuerySchema

bp = Blueprint("calendar", __name__, url_prefix="/api/calendar")
logger = logging.getLogger(__name__)

_create_schema = EventCreateSchema()
_update_schema = EventUpdateSchema()
_query_schema = EventListQuerySchema()


def _repo():
    return current_app.calendar_repo


@bp.get("/events")
def list_events():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400

    try:
        query = _query_schema.load({k: v for k, v in request.args.items() if k != "user_id"})
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 422

    events = _repo().list_events(user_id, start=query.get("start"), end=query.get("end"))
    return jsonify(events)


@bp.post("/events")
def create_event():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400

    try:
        data = _create_schema.load(request.get_json(force=True) or {})
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 422

    event = _repo().create_event(
        user_id=user_id,
        title=data["title"],
        description=data.get("description", ""),
        start_time=data["start_time"],
        end_time=data["end_time"],
        priority=data["priority"],
        is_flexible=data["is_flexible"],
    )
    return jsonify(event), 201


@bp.get("/events/<event_id>")
def get_event(event_id: str):
    event = _repo().get_event(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    return jsonify(event)


@bp.put("/events/<event_id>")
def update_event(event_id: str):
    try:
        data = _update_schema.load(request.get_json(force=True) or {})
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 422

    try:
        event = _repo().update_event(event_id, **data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    return jsonify(event)


@bp.delete("/events/<event_id>")
def delete_event(event_id: str):
    event = _repo().get_event(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    _repo().delete_event(event_id)
    return "", 204


@bp.post("/events/<event_id>/complete")
def complete_event(event_id: str):
    """
    Mark a review event as completed: record a review for the linked topic,
    resetting its decay to 0%, then delete the event from the calendar.
    """
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400

    event = _repo().get_event(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404

    proposal = _repo().get_proposal_by_event_id(event_id)
    if not proposal:
        return jsonify({"error": "No review topic linked to this event"}), 404

    topic_id = proposal["topic_id"]
    current_app.knowledge_engine._repo.record_review(topic_id, user_id, duration_minutes=60)
    _repo().delete_event(event_id)

    logger.info("Completed review for topic %s via event %s", topic_id, event_id)
    return jsonify({"topic_id": topic_id, "message": "Review recorded and event removed"})


@bp.get("/flexible-slots")
def flexible_slots():
    from datetime import datetime, timezone

    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400

    slots = _repo().get_flexible_slots(user_id, after=datetime.now(timezone.utc))
    return jsonify(slots)
