"""
FactLens Data Models
Pydantic schemas for the fact-checking pipeline.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────

class VerdictCategory(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    MISLEADING = "MISLEADING"
    UNVERIFIED = "UNVERIFIED"


class MessageType(str, Enum):
    TRANSCRIPT = "transcript"
    VERDICT = "verdict"
    STATUS = "status"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


# ── Core Models ──────────────────────────────────────────

class Claim(BaseModel):
    """A single verifiable factual claim extracted from transcript."""
    claim_text: str = Field(..., description="The factual claim to verify")
    speaker: str = Field(default="Unknown", description="Who made the claim")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="When the claim was made",
    )
    category: str = Field(
        default="general", description="Category of the claim"
    )


class SearchResult(BaseModel):
    """A single web search result."""
    title: str
    url: str
    content: str
    score: float = Field(default=0.0, description="Relevance score")


class Evidence(BaseModel):
    """A chunk of evidence stored in the vector database."""
    text: str
    source_url: str = ""
    source_title: str = ""
    similarity_score: float = 0.0


class Verdict(BaseModel):
    """The fact-check verdict for a claim."""
    claim_text: str
    verdict: VerdictCategory
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score 0-1"
    )
    explanation: str = Field(
        ..., description="Human-readable explanation of the verdict"
    )
    sources: list[str] = Field(
        default_factory=list, description="URLs of supporting sources"
    )
    reasoning: str = Field(
        default="", description="Detailed reasoning chain"
    )
    speaker: str = "Unknown"
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )


class FactCheckResult(BaseModel):
    """Complete result for a transcript chunk."""
    session_id: str
    claims: list[Claim] = Field(default_factory=list)
    verdicts: list[Verdict] = Field(default_factory=list)
    processed_at: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )


# ── WebSocket Messages ───────────────────────────────────

class WSMessage(BaseModel):
    """Base WebSocket message."""
    type: MessageType
    data: dict = Field(default_factory=dict)


class TranscriptMessage(BaseModel):
    """Incoming transcript from Chrome extension."""
    type: MessageType = MessageType.TRANSCRIPT
    text: str
    speaker: str = "Unknown"
    session_id: str = "default"
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )


class VerdictMessage(BaseModel):
    """Outgoing verdict to Chrome extension."""
    type: MessageType = MessageType.VERDICT
    verdicts: list[Verdict]
    session_id: str
