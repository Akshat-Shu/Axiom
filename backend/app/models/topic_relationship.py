import uuid
from app.extensions import db

VALID_RELATIONSHIP_TYPES = ("prerequisite", "related", "extends", "contrasts")


class TopicRelationship(db.Model):
    __tablename__ = "topic_relationships"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_topic_id = db.Column(db.String(36), db.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    target_topic_id = db.Column(db.String(36), db.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    relationship_type = db.Column(db.String(50), nullable=False)
    strength = db.Column(db.Float, nullable=False, default=0.5)

    __table_args__ = (
        db.CheckConstraint("strength >= 0 AND strength <= 1", name="ck_relationship_strength_range"),
        db.UniqueConstraint("source_topic_id", "target_topic_id", "relationship_type", name="uq_topic_relationship"),
    )

    source_topic = db.relationship("Topic", foreign_keys=[source_topic_id], back_populates="outgoing_relationships")
    target_topic = db.relationship("Topic", foreign_keys=[target_topic_id], back_populates="incoming_relationships")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_topic_id": self.source_topic_id,
            "target_topic_id": self.target_topic_id,
            "relationship_type": self.relationship_type,
            "strength": round(self.strength, 4),
        }
