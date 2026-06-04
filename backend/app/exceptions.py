"""
Domain-level exceptions shared across engines and the API layer.

This module intentionally has NO dependencies on Flask, SQLAlchemy, or any
concrete implementation — keeping it safe to import from both high-level
engines and the API without violating the Dependency Inversion Principle.
"""


class EventConflictError(ValueError):
    """
    Raised when a calendar mutation would create a time overlap, or when a
    requested change is otherwise not permitted (e.g. moving a non-flexible
    event). Carries the conflicting events so callers can surface details.
    """

    def __init__(self, message: str, conflicts: list[dict] | None = None):
        super().__init__(message)
        self.message = message
        self.conflicts = conflicts or []
