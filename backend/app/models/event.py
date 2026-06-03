import uuid
from datetime import datetime, timezone
from app.extensions import db


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime(timezone=True), nullable=False)
    end_time = db.Column(db.DateTime(timezone=True), nullable=False)
    priority = db.Column(db.Integer, nullable=False, default=3)
    is_flexible = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.CheckConstraint("priority >= 1 AND priority <= 5", name="ck_event_priority_range"),
        db.CheckConstraint("end_time > start_time", name="ck_event_end_after_start"),
    )

    user = db.relationship("User", back_populates="events")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "priority": self.priority,
            "is_flexible": self.is_flexible,
            "created_at": self.created_at.isoformat(),
        }
