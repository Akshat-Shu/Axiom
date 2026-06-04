import uuid
from datetime import datetime, timezone
from app.extensions import db
from app.time_utils import iso_utc

PROPOSAL_STATUSES = ("pending", "accepted", "declined")


class ScheduleProposal(db.Model):
    __tablename__ = "schedule_proposals"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id = db.Column(db.String(36), db.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    original_event_id = db.Column(db.String(36), db.ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    proposed_event_id = db.Column(db.String(36), db.ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    ai_reasoning = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('pending', 'accepted', 'declined')",
            name="ck_proposal_status",
        ),
    )

    user = db.relationship("User", back_populates="proposals")
    topic = db.relationship("Topic", back_populates="proposals")
    original_event = db.relationship("Event", foreign_keys=[original_event_id])
    proposed_event = db.relationship("Event", foreign_keys=[proposed_event_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "topic_id": self.topic_id,
            "topic_title": self.topic.title if self.topic else None,
            "topic_decay_score": round(self.topic.decay_score, 4) if self.topic else 0.0,
            "original_event_id": self.original_event_id,
            "proposed_event_id": self.proposed_event_id,
            "proposed_event_title": self.proposed_event.title if self.proposed_event else None,
            "proposed_event_start": iso_utc(self.proposed_event.start_time) if self.proposed_event else None,
            "ai_reasoning": self.ai_reasoning,
            "status": self.status,
            "created_at": iso_utc(self.created_at),
        }
