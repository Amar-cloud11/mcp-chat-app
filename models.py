from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request sent by the chat frontend."""

    query: str = Field(
        ...,
        min_length=1,
        description="The user's question or message",
    )


class ChatResponse(BaseModel):
    """Response returned by the backend."""

    answer: str = Field(
        ...,
        description="The assistant's answer",
    )
