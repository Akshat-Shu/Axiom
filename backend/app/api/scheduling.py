import logging
from flask import Blueprint, request, jsonify, current_app

from app.exceptions import EventConflictError

bp = Blueprint("scheduling", __name__, url_prefix="/api/scheduling")
logger = logging.getLogger(__name__)


def _engine():
    return current_app.scheduling_engine


@bp.post("/analyze")
def analyze():
    """Trigger decay recalculation and generate AI scheduling proposals."""
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400

    threshold = float(request.args.get("threshold", 0.3))

    current_app.knowledge_engine.recalculate_decay(user_id)

    try:
        proposals = _engine().generate_proposals(user_id, decay_threshold=threshold)
    except Exception as exc:
        logger.exception("Proposal generation failed")
        return jsonify({"error": "Proposal generation failed", "detail": str(exc)}), 500

    return jsonify({"proposals_created": len(proposals), "proposals": proposals})


@bp.get("/proposals")
def list_proposals():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400

    status = request.args.get("status")
    proposals = current_app.calendar_repo.list_proposals(user_id, status=status)
    return jsonify(proposals)


@bp.post("/proposals/<proposal_id>/accept")
def accept_proposal(proposal_id: str):
    try:
        proposal = _engine().accept_proposal(proposal_id)
    except EventConflictError as exc:
        return jsonify({"error": str(exc), "conflicts": exc.conflicts}), 409
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Accept proposal failed")
        return jsonify({"error": str(exc)}), 500
    return jsonify(proposal)


@bp.post("/proposals/<proposal_id>/decline")
def decline_proposal(proposal_id: str):
    try:
        proposal = _engine().decline_proposal(proposal_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Decline proposal failed")
        return jsonify({"error": str(exc)}), 500
    return jsonify(proposal)


@bp.post("/proposals/<proposal_id>/chat")
def chat_proposal(proposal_id: str):
    data = request.get_json(force=True) or {}
    try:
        result = _engine().chat_about_proposal(
            proposal_id,
            messages=data.get("messages", []),
            user_message=data.get("message", ""),
            client_now=data.get("now"),
            tz_name=data.get("timezone", "UTC"),
            utc_offset_minutes=data.get("utc_offset_minutes", 0),
        )
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        logger.exception("Proposal chat failed")
        return jsonify({"error": str(exc)}), 500


@bp.post("/proposals/<proposal_id>/apply")
def apply_proposal(proposal_id: str):
    data = request.get_json(force=True) or {}
    try:
        proposal = _engine().apply_proposal_changes(proposal_id, changes=data.get("changes", []))
        return jsonify(proposal)
    except EventConflictError as exc:
        return jsonify({"error": str(exc), "conflicts": exc.conflicts}), 409
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Apply proposal failed")
        return jsonify({"error": str(exc)}), 500
