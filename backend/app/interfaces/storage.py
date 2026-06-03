from abc import ABC, abstractmethod


class StorageService(ABC):
    """
    Abstraction for binary object storage.
    High-level modules (KnowledgeEngine) depend on this, never on S3 directly.
    """

    @abstractmethod
    def upload(self, file_key: str, data: bytes, content_type: str) -> str:
        """Upload bytes and return a permanent retrieval key."""

    @abstractmethod
    def download(self, file_key: str) -> bytes:
        """Download and return the raw bytes for a stored object."""

    @abstractmethod
    def delete(self, file_key: str) -> None:
        """Permanently remove a stored object."""

    @abstractmethod
    def get_presigned_url(self, file_key: str, expires_in: int = 3600) -> str:
        """Return a time-limited URL for direct client access."""
