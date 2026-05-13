"""
Pydantic schemas for the Memory SDK.

All data flowing between components must be validated through these models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MemoryPayload(BaseModel):
    """Raw chat transcript submitted for consolidation.

    Attributes:
        session_id: Unique identifier for the conversation session.
        user_id: Caller-supplied identifier for the end user (auth is the
            parent application's responsibility).
        messages: Ordered list of chat messages as ``{"role": ..., "content": ...}``
            dicts.
        timestamp: When the payload was captured; defaults to now (UTC).
    """

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    messages: list[dict[str, str]]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExtractedFact(BaseModel):
    """A single high-fidelity fact produced by the consolidation worker.

    Facts must preserve exact technical phrasing — never high-level summaries.

    Attributes:
        memory_id: Unique identifier; used as the upsert key in the archive.
        user_id: Owning user; propagated from the originating ``MemoryPayload``.
        session_id: Source session the fact was extracted from.
        fact_text: The resolved, detailed fact text.  Pronouns must be fully
            resolved to explicit entities before storage.
        importance_score: Float in ``[0.0, 1.0]`` indicating salience.
            Values above ``0.85`` trigger hot consolidation.
        timestamp: UTC time at which the fact was extracted.
    """

    memory_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    session_id: str
    fact_text: str
    importance_score: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SubstrateSection(BaseModel):
    """A single keyed section of the Active Substrate Markdown state.

    The ``section_name`` maps to a Markdown level-2 header (``## <name>``);
    ``content`` is the freeform text block stored under that header.

    Attributes:
        section_name: The Markdown section header (without ``##``).
        content: Detailed text content for the section.
    """

    section_name: str
    content: str


class SearchQuery(BaseModel):
    """Parameters for a hybrid archive search.

    Hybrid search blends dense (semantic) and sparse (BM25 / full-text) retrieval.
    Weights must sum to ``1.0``; the SDK does not enforce this automatically so
    callers should validate before submission.

    Attributes:
        query: Natural-language search string.
        dense_weight: Weight applied to the dense semantic retrieval score
            (default ``0.7``).
        sparse_weight: Weight applied to the sparse keyword retrieval score
            (default ``0.3``).
        top_k: Maximum number of results to return (default ``10``).
        user_id: When provided, restricts results to this user's memories.
        before: Return only facts extracted before this UTC datetime.
        after: Return only facts extracted after this UTC datetime.
        offset: Pagination offset — skip this many results before returning
            ``top_k`` (default ``0``).
    """

    query: str
    dense_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    sparse_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    top_k: int = Field(default=10, ge=1)
    user_id: Optional[str] = None
    before: Optional[datetime] = None
    after: Optional[datetime] = None
    offset: int = Field(default=0, ge=0)
