import uuid
from datetime import datetime, timezone
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    topics = db.relationship("Topic", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    events = db.relationship("Event", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    proposals = db.relationship("ScheduleProposal", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    reviews = db.relationship("ReviewSession", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "created_at": self.created_at.isoformat(),
        }
