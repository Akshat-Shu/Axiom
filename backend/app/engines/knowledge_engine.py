"""
KnowledgeEngine — high-level orchestration for document ingestion and decay scoring.

DIP: depends on StorageService, LLMService, and KnowledgeRepository abstractions.
No concrete class (S3, OpenRouter, PostgreSQL) is referenced here.
"""
import json
import logging
import math
import uuid
from datetime import datetime, timezone

from app.interfaces.knowledge_repository import KnowledgeRepository
from app.interfaces.llm import LLMService
from app.interfaces.storage import StorageService

logger = logging.getLogger(__name__)


def _as_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (UTC). Handles SQLite naive datetimes."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


DECAY_HALF_LIFE_DAYS = 14  # overridden at runtime by config.DECAY_HALF_LIFE_DAYS

EXTRACTION_SYSTEM_PROMPT = """
You are an expert knowledge analyst. Given raw text from a user's notes or documents,
extract the core topics and their relationships. Return ONLY valid JSON with this structure:
{
  "primary_title": "string — the single main topic name",
  "summary": "string — 2-3 sentence summary of the content",
  "subtopics": [
    {"title": "string", "summary": "string"}
  ],
  "relationships": [
    {
      "source": "string — title of source topic",
      "target": "string — title of target topic",
      "type": "prerequisite|related|extends|contrasts",
      "strength": 0.0-1.0
    }
  ]
}

IMPORTANT RULES:
- Extract only meaningful academic or subject-matter topics from the actual content.
- NEVER create topics named after PDF internals such as "PDF Structure", "PDF Metadata",
  "PDF Object", "PDF Header", "PDF Stream", "Cross-Reference Table", or similar.
- If the text is empty, too short, or appears to be binary/structural data rather than
  real content, return an empty subtopics list and set primary_title to "Untitled Document".
- Topics should reflect what the document is ABOUT, not how it is formatted or stored.
""".strip()


class KnowledgeEngine:
    def __init__(
        self,
        storage: StorageService,
        llm: LLMService,
        repo: KnowledgeRepository,
        half_life_days: float = DECAY_HALF_LIFE_DAYS,
    ):
        self._storage = storage
        self._llm = llm
        self._repo = repo
        self._half_life_days = half_life_days

    def ingest_document(self, user_id: str, filename: str, raw_bytes: bytes, content_type: str) -> dict:
        """
        Upload the raw file to storage, extract topics via LLM, persist to DB.
        Returns the created primary topic dict.
        """
        file_key = f"uploads/{user_id}/{uuid.uuid4()}/{filename}"
        self._storage.upload(file_key, raw_bytes, content_type)
        logger.info("Stored document at key %s", file_key)

        text_content = self._extract_text(raw_bytes, content_type)

        if len(text_content.strip()) < 50:
            logger.warning("Extracted text too short for %s (%d chars), skipping LLM", filename, len(text_content.strip()))
            extraction = {"primary_title": filename, "summary": "Could not extract readable text from this document.", "subtopics": [], "relationships": []}
        else:
            try:
                extraction_json = self._llm.complete(
                    system_prompt=EXTRACTION_SYSTEM_PROMPT,
                    user_message=f"Analyze the following text:\n\n{text_content[:8000]}",
                    json_mode=True,
                )
                extraction = json.loads(extraction_json)
            except Exception as exc:
                logger.error("LLM extraction failed: %s", exc)
                extraction = {"primary_title": filename, "summary": "", "subtopics": [], "relationships": []}

        primary = self._repo.create_topic(
            user_id=user_id,
            title=extraction.get("primary_title", filename),
            content_summary=extraction.get("summary", ""),
            file_key=file_key,
        )

        topic_id_map: dict[str, str] = {primary["title"]: primary["id"]}

        for sub in extraction.get("subtopics", []):
            sub_topic = self._repo.create_topic(
                user_id=user_id,
                title=sub.get("title", "Unnamed"),
                content_summary=sub.get("summary", ""),
                file_key=None,
            )
            topic_id_map[sub_topic["title"]] = sub_topic["id"]

        for rel in extraction.get("relationships", []):
            source_id = topic_id_map.get(rel.get("source"))
            target_id = topic_id_map.get(rel.get("target"))
            if source_id and target_id and source_id != target_id:
                try:
                    self._repo.create_relationship(
                        source_id=source_id,
                        target_id=target_id,
                        rel_type=rel.get("type", "related"),
                        strength=float(rel.get("strength", 0.5)),
                    )
                except Exception as exc:
                    logger.warning("Could not create relationship: %s", exc)

        return primary

    def recalculate_decay(self, user_id: str) -> list[dict]:
        """
        Recompute decay scores for all user topics using exponential decay.
        Returns updated topic dicts sorted by decay score descending.
        """
        topics = self._repo.list_topics(user_id)
        now = datetime.now(timezone.utc)
        updated = []

        for topic in topics:
            last_reviewed = topic.get("last_reviewed_at")
            if last_reviewed:
                reviewed_dt = _as_utc(datetime.fromisoformat(last_reviewed))
                days_elapsed = (now - reviewed_dt).total_seconds() / 86400
            else:
                created_at = _as_utc(datetime.fromisoformat(topic["created_at"]))
                days_elapsed = (now - created_at).total_seconds() / 86400

            decay = 1.0 - math.exp(-math.log(2) * days_elapsed / self._half_life_days)
            decay = round(min(1.0, max(0.0, decay)), 4)
            self._repo.update_decay_score(topic["id"], decay)
            topic["decay_score"] = decay
            updated.append(topic)

        updated.sort(key=lambda t: t["decay_score"], reverse=True)
        logger.info("Recalculated decay for %d topics (user %s)", len(updated), user_id)
        return updated

    def get_knowledge_graph(self, user_id: str) -> dict:
        """Return nodes + edges suitable for a graph visualisation."""
        topics = self._repo.list_topics(user_id)
        relationships = self._repo.list_relationships(user_id)
        return {
            "nodes": [{"id": t["id"], "label": t["title"], "decay_score": t["decay_score"]} for t in topics],
            "edges": [
                {
                    "id": r["id"],
                    "source": r["source_topic_id"],
                    "target": r["target_topic_id"],
                    "type": r["relationship_type"],
                    "strength": r["strength"],
                }
                for r in relationships
            ],
        }

    @staticmethod
    def _extract_text(raw_bytes: bytes, content_type: str) -> str:
        """Extract clean plain text from uploaded file bytes."""
        if "pdf" in content_type or raw_bytes[:4] == b"%PDF":
            return KnowledgeEngine._extract_pdf(raw_bytes)
        return raw_bytes.decode("utf-8", errors="replace")

    @staticmethod
    def _extract_pdf(raw_bytes: bytes) -> str:
        import io
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw_bytes))
            pages = []
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text.strip())
            return "\n\n".join(pages)
        except Exception as exc:
            logger.warning("PDF extraction failed: %s", exc)
            return ""
