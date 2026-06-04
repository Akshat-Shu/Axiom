from abc import ABC, abstractmethod
from typing import Optional


class UserRepository(ABC):
    """
    Abstraction for user persistence.
    The API layer depends on this; PostgreSQL is one concrete implementation.
    """

    @abstractmethod
    def create_user(self, email: str, username: str) -> dict:
        """Persist a new user and return its dict representation."""
        pass

    @abstractmethod
    def get_user(self, user_id: str) -> Optional[dict]:
        """Return the user by id, or None if not found."""
        pass

    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[dict]:
        """Return the user with the given email, or None if not found."""
        pass
