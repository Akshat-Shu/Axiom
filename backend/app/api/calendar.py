import logging
from flask import Blueprint, request, jsonify, current_app
from marshmallow import ValidationError

from app.schemas.event_schema import EventCreateSchema, EventUpdateSchema, EventListQuerySchema
from app.exceptions import EventConflictError

bp = Blueprint("calendar", __name__, url_prefix="/api/calendar")
logger = logging.getLogger(__name__)

_create_schema = EventCreateSchema()
_update_schema = EventUpdateSchema()
_query_schema = EventListQuerySchema()


def _engine():
    return current_app.calendar_engine


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

    # Auto-complete any events whose end time has passed (and reset linked decay).
    current_app.scheduling_engine.reconcile_completions(user_id)

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

    try:
        event = _engine().create_event(
            user_id=user_id,
            title=data["title"],
            description=data.get("description", ""),
            start_time=data["start_time"],
            end_time=data["end_time"],
            priority=data["priority"],
            is_flexible=data["is_flexible"],
        )
    except EventConflictError as exc:
        return jsonify({"error": str(exc), "conflicts": exc.conflicts}), 409

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
        event = _engine().update_event(event_id, **data)
    except EventConflictError as exc:
        return jsonify({"error": str(exc), "conflicts": exc.conflicts}), 409
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
    Mark an event completed (it turns green on the calendar). If the event is a
    review session linked to a knowledge topic, that topic's decay is reset to 0.
    """
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400

    try:
        event = current_app.scheduling_engine.complete_event(event_id, user_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404

    return jsonify(event)


@bp.get("/flexible-slots")
def flexible_slots():
    from datetime import datetime, timezone

    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400

    slots = _repo().get_flexible_slots(user_id, after=datetime.now(timezone.utc))
    return jsonify(slots)
