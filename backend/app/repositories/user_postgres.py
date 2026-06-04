import logging
from typing import Optional

from app.extensions import db
from app.interfaces.user_repository import UserRepository
from app.models import User

logger = logging.getLogger(__name__)


class PostgreSQLUserRepository(UserRepository):
    """Concrete UserRepository backed by PostgreSQL via SQLAlchemy."""

    def create_user(self, email: str, username: str) -> dict:
        user = User(email=email, username=username)
        db.session.add(user)
        db.session.commit()
        logger.info("Created user %s (%s)", user.id, email)
        return user.to_dict()

    def get_user(self, user_id: str) -> Optional[dict]:
        user = db.session.get(User, user_id)
        return user.to_dict() if user else None

    def get_user_by_email(self, email: str) -> Optional[dict]:
        user = db.session.query(User).filter_by(email=email).first()
        return user.to_dict() if user else None
