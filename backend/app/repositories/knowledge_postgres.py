import logging
from datetime import datetime, timezone
from typing import Optional

from app.extensions import db
from app.interfaces.knowledge_repository import KnowledgeRepository
from app.models import Topic, TopicRelationship, ReviewSession

logger = logging.getLogger(__name__)


class PostgreSQLKnowledgeRepository(KnowledgeRepository):
    """Concrete KnowledgeRepository backed by PostgreSQL via SQLAlchemy."""

    def create_topic(self, user_id: str, title: str, content_summary: str, file_key: Optional[str]) -> dict:
        topic = Topic(
            user_id=user_id,
            title=title,
            content_summary=content_summary,
            file_key=file_key,
        )
        db.session.add(topic)
        db.session.commit()
        logger.info("Created topic %s for user %s", topic.id, user_id)
        return topic.to_dict()

    def get_topic(self, topic_id: str) -> Optional[dict]:
        topic = db.session.get(Topic, topic_id)
        return topic.to_dict() if topic else None

    def list_topics(self, user_id: str) -> list[dict]:
        topics = db.session.query(Topic).filter_by(user_id=user_id).order_by(Topic.decay_score.desc()).all()
        return [t.to_dict() for t in topics]

    def update_decay_score(self, topic_id: str, score: float) -> None:
        topic = db.session.get(Topic, topic_id)
        if topic:
            topic.decay_score = max(0.0, min(1.0, score))
            db.session.commit()

    def record_review(self, topic_id: str, user_id: str, duration_minutes: int) -> None:
        now = datetime.now(timezone.utc)
        review = ReviewSession(
            user_id=user_id,
            topic_id=topic_id,
            reviewed_at=now,
            duration_minutes=duration_minutes,
        )
        db.session.add(review)
        topic = db.session.get(Topic, topic_id)
        if topic:
            topic.last_reviewed_at = now
            topic.decay_score = 0.0
        db.session.commit()

    def delete_topic(self, topic_id: str) -> None:
        topic = db.session.get(Topic, topic_id)
        if topic:
            db.session.delete(topic)
            db.session.commit()
            logger.info("Deleted topic %s", topic_id)

    def create_relationship(self, source_id: str, target_id: str, rel_type: str, strength: float) -> dict:
        rel = TopicRelationship(
            source_topic_id=source_id,
            target_topic_id=target_id,
            relationship_type=rel_type,
            strength=strength,
        )
        db.session.add(rel)
        db.session.commit()
        return rel.to_dict()

    def list_relationships(self, user_id: str) -> list[dict]:
        rels = (
            db.session.query(TopicRelationship)
            .join(Topic, Topic.id == TopicRelationship.source_topic_id)
            .filter(Topic.user_id == user_id)
            .all()
        )
        return [r.to_dict() for r in rels]

    def get_decaying_topics(self, user_id: str, threshold: float = 0.3) -> list[dict]:
        topics = (
            db.session.query(Topic)
            .filter(
                Topic.user_id == user_id,
                db.or_(
                    Topic.decay_score >= threshold,
                    Topic.last_reviewed_at == None,  # noqa: E711 — SQLAlchemy requires == None
                ),
            )
            .order_by(Topic.decay_score.desc())
            .all()
        )
        return [t.to_dict() for t in topics]
