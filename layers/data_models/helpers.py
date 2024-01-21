"""Helper data models."""

from pydantic import BaseModel


class SuccessResponse(BaseModel):
    """Success response for simple http request."""

    message: str
