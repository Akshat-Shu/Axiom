import logging
from flask import Blueprint, request, jsonify, current_app
from marshmallow import ValidationError

from app.schemas.user_schema import UserCreateSchema

bp = Blueprint("users", __name__, url_prefix="/api/users")
logger = logging.getLogger(__name__)
_create_schema = UserCreateSchema()


def _repo():
    return current_app.user_repo


@bp.post("")
def create_user():
    try:
        data = _create_schema.load(request.get_json(force=True) or {})
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 422

    if _repo().get_user_by_email(data["email"]):
        return jsonify({"error": "Email already registered"}), 409

    user = _repo().create_user(email=data["email"], username=data["username"])
    return jsonify(user), 201


@bp.get("/<user_id>")
def get_user(user_id: str):
    user = _repo().get_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)
