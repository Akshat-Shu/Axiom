import logging
from flask import Blueprint, request, jsonify, current_app
from marshmallow import ValidationError

from app.schemas.topic_schema import ReviewSchema

bp = Blueprint("knowledge", __name__, url_prefix="/api/knowledge")
logger = logging.getLogger(__name__)
_review_schema = ReviewSchema()


def _engine():
    return current_app.knowledge_engine


@bp.post("/upload")
def upload_document():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400

    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "File has no filename"}), 400

    raw_bytes = file.read()
    if not raw_bytes:
        return jsonify({"error": "Uploaded file is empty"}), 400

    try:
        topic = _engine().ingest_document(
            user_id=user_id,
            filename=file.filename,
            raw_bytes=raw_bytes,
            content_type=file.content_type or "application/octet-stream",
        )
    except Exception as exc:
        logger.exception("Document ingestion failed")
        return jsonify({"error": "Ingestion failed", "detail": str(exc)}), 500

    return jsonify(topic), 201


@bp.get("/topics")
def list_topics():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400
    topics = _engine()._repo.list_topics(user_id)
    return jsonify(topics)


@bp.get("/topics/<topic_id>")
def get_topic(topic_id: str):
    topic = _engine()._repo.get_topic(topic_id)
    if not topic:
        return jsonify({"error": "Topic not found"}), 404
    return jsonify(topic)


@bp.delete("/topics/<topic_id>")
def delete_topic(topic_id: str):
    topic = _engine()._repo.get_topic(topic_id)
    if not topic:
        return jsonify({"error": "Topic not found"}), 404
    _engine()._repo.delete_topic(topic_id)
    return "", 204


@bp.post("/topics/<topic_id>/review")
def record_review(topic_id: str):
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400

    try:
        data = _review_schema.load(request.get_json(force=True) or {})
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 422

    topic = _engine()._repo.get_topic(topic_id)
    if not topic:
        return jsonify({"error": "Topic not found"}), 404

    _engine()._repo.record_review(topic_id, user_id, data["duration_minutes"])
    return jsonify({"message": "Review recorded", "topic_id": topic_id})


@bp.post("/decay/recalculate")
def recalculate_decay():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400
    topics = _engine().recalculate_decay(user_id)
    return jsonify({"updated": len(topics), "topics": topics})


@bp.get("/graph")
def get_graph():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400
    graph = _engine().get_knowledge_graph(user_id)
    return jsonify(graph)
