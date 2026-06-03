import logging
from flask import Blueprint, request, jsonify, current_app
from marshmallow import ValidationError

from app.extensions import db
from app.models import User
from app.schemas.user_schema import UserCreateSchema

bp = Blueprint("users", __name__, url_prefix="/api/users")
logger = logging.getLogger(__name__)
_create_schema = UserCreateSchema()


@bp.post("")
def create_user():
    try:
        data = _create_schema.load(request.get_json(force=True) or {})
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 422

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(email=data["email"], username=data["username"])
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201


@bp.get("/<user_id>")
def get_user(user_id: str):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict())
