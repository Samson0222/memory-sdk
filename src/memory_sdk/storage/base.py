"""
Abstract Base Classes for all Memory SDK storage backends.

Every concrete storage implementation — whether PostgreSQL, Qdrant, local JSON,
or a future provider — MUST inherit from these ABCs and implement every abstract
method.  Core SDK logic (archive.py, substrate.py, client.py) depends ONLY on
these interfaces; it must never import from a concrete backend module directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from memory_sdk.schemas import ExtractedFact, SearchQuery, SubstrateSection


class BaseVectorStore(ABC):
    """Interface for the Deep Archive (Camp 1) vector storage backend.

    Concrete implementations must provide async ingest and search operations
    backed by a vector database (pgvector, Qdrant, etc.).  All methods are
    declared ``async`` to prevent blocking in the consolidation worker's
    event loop.
    """

    @abstractmethod
    async def ingest(
        self,
        user_id: str,
        facts: list[ExtractedFact],
    ) -> list[str]:
        """Upsert extracted facts into the vector archive.

        Implementations must:
        - Embed each fact's ``fact_text`` before insertion.
        - Perform a semantic similarity check against existing records and skip
          any fact whose nearest neighbour exceeds the configured
          ``DEDUP_SIMILARITY_THRESHOLD`` (default ``0.95``).
        - Store the full metadata schema: ``memory_id``, ``user_id``,
          ``timestamp``, ``session_id``, and ``importance_score``.

        Args:
            user_id: Owning user; used to scope reads in ``'server'`` mode.
            facts: List of validated ``ExtractedFact`` objects to persist.

        Returns:
            List of ``memory_id`` strings for every fact that was actually
            inserted (duplicates are excluded).
        """
        ...

    @abstractmethod
    async def hybrid_search(
        self,
        query: SearchQuery,
    ) -> list[ExtractedFact]:
        """Execute a hybrid dense + sparse retrieval against the archive.

        When ``HYBRID_SEARCH_ENABLED`` is ``False``, implementations may fall
        back to dense-only search but must still honour the ``top_k`` and
        ``offset`` pagination fields.

        Results must be exact, detailed chunks — never summarised content.

        Args:
            query: A ``SearchQuery`` containing the query string, blend weights,
                pagination parameters, and optional temporal / user filters.

        Returns:
            Ordered list of ``ExtractedFact`` objects ranked by combined score,
            length-bounded by ``query.top_k`` starting at ``query.offset``.
        """
        ...

    @abstractmethod
    async def delete(self, user_id: str, memory_id: str) -> bool:
        """Permanently remove a single fact from the archive.

        Args:
            user_id: Must match the owning user of the record (enforced in
                ``'server'`` mode).
            memory_id: The unique identifier of the fact to delete.

        Returns:
            ``True`` if a record was found and deleted; ``False`` if no record
            matched ``memory_id``.
        """
        ...


class BaseStateStore(ABC):
    """Interface for the Active Substrate (Camp 2) mutable state backend.

    The Substrate stores a per-user JSON document whose keys map to Markdown
    section headers and whose values are freeform text blocks.  Concrete
    implementations may persist this document in PostgreSQL (JSONB column),
    on-disk JSON files, or any other key-value store.

    All methods are async to allow seamless swapping between local and remote
    backends without API changes.
    """

    @abstractmethod
    async def get_sections(
        self,
        user_id: str,
        section_names: Optional[list[str]] = None,
    ) -> list[SubstrateSection]:
        """Retrieve one or more sections from the user's Substrate.

        Used to inject targeted context into the active conversation window
        without loading the entire state document.

        Args:
            user_id: Owning user whose Substrate to read.
            section_names: If provided, return only the sections whose
                ``section_name`` appears in this list.  If ``None`` or empty,
                return all sections.

        Returns:
            List of ``SubstrateSection`` objects for the requested headers.
            Sections that do not yet exist are silently omitted (not an error).
        """
        ...

    @abstractmethod
    async def update_section(
        self,
        user_id: str,
        section_name: str,
        content: str,
    ) -> None:
        """Overwrite the full content of a Substrate section.

        Performs a deterministic state replacement — the previous value is
        discarded entirely.  Used by the consolidation worker when a conflict
        is detected (e.g. "PostgreSQL" → "Supabase").

        If the section does not yet exist it is created.

        Args:
            user_id: Owning user whose Substrate to modify.
            section_name: The target section header (without ``##``).
            content: New content to store verbatim.
        """
        ...

    @abstractmethod
    async def append_to_section(
        self,
        user_id: str,
        section_name: str,
        content: str,
    ) -> None:
        """Append content to an existing Substrate section.

        Unlike ``update_section``, this is an additive operation — existing
        content is preserved and the new content is concatenated after a
        newline separator.  If the section does not yet exist it is created
        with ``content`` as its initial value.

        Args:
            user_id: Owning user whose Substrate to modify.
            section_name: The target section header (without ``##``).
            content: Text to append to the section.
        """
        ...

    @abstractmethod
    async def delete_section(
        self,
        user_id: str,
        section_name: str,
    ) -> bool:
        """Remove an entire section from the user's Substrate.

        Args:
            user_id: Owning user whose Substrate to modify.
            section_name: The section header to remove (without ``##``).

        Returns:
            ``True`` if the section existed and was removed; ``False`` if it
            did not exist.
        """
        ...
