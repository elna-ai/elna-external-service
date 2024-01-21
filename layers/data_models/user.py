"""User related data models."""
from pydantic import BaseModel


class User(BaseModel):
    """User model."""

    principal: str
