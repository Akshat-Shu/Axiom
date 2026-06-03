import uuid
from datetime import datetime, timezone
from app.extensions import db


class ReviewSession(db.Model):
    __tablename__ = "review_sessions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id = db.Column(db.String(36), db.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    duration_minutes = db.Column(db.Integer, nullable=False, default=30)

    __table_args__ = (
        db.CheckConstraint("duration_minutes > 0", name="ck_review_duration_positive"),
    )

    user = db.relationship("User", back_populates="reviews")
    topic = db.relationship("Topic", back_populates="reviews")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "topic_id": self.topic_id,
            "reviewed_at": self.reviewed_at.isoformat(),
            "duration_minutes": self.duration_minutes,
        }
