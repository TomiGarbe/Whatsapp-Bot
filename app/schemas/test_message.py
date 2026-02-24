"""Schemas for test message endpoint."""

from pydantic import BaseModel, Field


class TestMessageRequest(BaseModel):
    """Request body for /test-message."""

    user: str = Field(..., description="User identifier", examples=["user_123"])
    message: str = Field(..., description="Inbound user message", examples=["Hola, que planes hay?"])


class TestMessageResponse(BaseModel):
    """Response payload for /test-message."""

    user: str
    response: str
