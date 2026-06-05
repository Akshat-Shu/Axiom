import uuid
from datetime import datetime, timezone
from app.extensions import db
from app.time_utils import iso_utc


class Topic(db.Model):
    __tablename__ = "topics"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content_summary = db.Column(db.Text, nullable=True)
    file_key = db.Column(db.String(512), nullable=True)
    decay_score = db.Column(db.Float, nullable=False, default=0.0)
    half_life_days = db.Column(db.Float, nullable=False, default=14.0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship("User", back_populates="topics")
    outgoing_relationships = db.relationship(
        "TopicRelationship",
        foreign_keys="TopicRelationship.source_topic_id",
        back_populates="source_topic",
        cascade="all, delete-orphan",
    )
    incoming_relationships = db.relationship(
        "TopicRelationship",
        foreign_keys="TopicRelationship.target_topic_id",
        back_populates="target_topic",
        cascade="all, delete-orphan",
    )
    reviews = db.relationship("ReviewSession", back_populates="topic", cascade="all, delete-orphan", lazy="dynamic")
    proposals = db.relationship("ScheduleProposal", back_populates="topic", lazy="dynamic")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "content_summary": self.content_summary,
            "file_key": self.file_key,
            "decay_score": round(self.decay_score, 4),
            "half_life_days": self.half_life_days,
            "created_at": iso_utc(self.created_at),
            "last_reviewed_at": iso_utc(self.last_reviewed_at),
        }
