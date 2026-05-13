"""
Central configuration for the Memory SDK.

All tuneable knobs live here.  Values are loaded from environment variables
(or a ``.env`` file) via ``pydantic-settings``.  Import the singleton
``settings`` object rather than instantiating ``MemoryConfig`` directly.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MemoryConfig(BaseSettings):
    """SDK-wide settings loaded from environment variables.

    Attributes:
        RUN_MODE: Controls execution isolation.

            - ``'local'``: Bypass user-ID filtering; intended for single-user
              local development.
            - ``'server'``: Enforce strict ``user_id`` scoping on every query
              and mutation.

        VECTOR_DB_TYPE: Which vector store backend to instantiate.

            - ``'pgvector'``: PostgreSQL with the pgvector extension (primary).
            - ``'qdrant'``: Qdrant (fallback / existing RAG infrastructure).

        STATE_DB_TYPE: Which state store backend to use for the Active Substrate.

            - ``'postgresql'``: Persist substrate sections in a JSONB column.
            - ``'local_json'``: Persist substrate sections as JSON files on disk
              (development / offline mode).

        HYBRID_SEARCH_ENABLED: When ``True``, archive queries blend dense
            semantic search with sparse BM25 / full-text retrieval.  When
            ``False``, only dense search is performed.

        EMBEDDING_PROVIDER: Name of the embedding provider to use.
            Informational — the storage layer resolves the actual client.

        EMBEDDING_MODEL: Model name passed to the embedding provider.
        EMBEDDING_DIMENSION: Dimensionality of the embedding vectors.
        DEDUP_SIMILARITY_THRESHOLD: Cosine similarity above which a candidate
            fact is considered a duplicate and skipped during ingestion.
        HOT_CONSOLIDATION_THRESHOLD: ``importance_score`` above which the
            consolidation worker triggers immediately rather than waiting for
            end-of-session.

        POSTGRES_DSN: Full asyncpg connection string for PostgreSQL backends.
        QDRANT_URL: HTTP URL for the Qdrant service.
        QDRANT_API_KEY: Optional API key for authenticated Qdrant instances.
        QDRANT_COLLECTION: Name of the Qdrant collection used for the archive.

        LOCAL_JSON_DIR: Directory path for ``local_json`` substrate files.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Execution mode ---
    RUN_MODE: Literal["local", "server"] = Field(
        default="local",
        description="Isolation mode: 'local' skips user-ID scoping; 'server' enforces it.",
    )

    # --- Storage backends ---
    VECTOR_DB_TYPE: Literal["pgvector", "qdrant"] = Field(
        default="pgvector",
        description="Vector store backend to use for the Deep Archive.",
    )
    STATE_DB_TYPE: Literal["postgresql", "local_json"] = Field(
        default="local_json",
        description="State store backend for the Active Substrate.",
    )

    # --- Feature flags ---
    HYBRID_SEARCH_ENABLED: bool = Field(
        default=True,
        description="Enable dense+sparse hybrid retrieval in the archive.",
    )

    # --- Embedding ---
    EMBEDDING_PROVIDER: str = Field(
        default="openai",
        description="Embedding provider name (openai, voyageai, local, …).",
    )
    EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small",
        description="Model name passed to the embedding provider.",
    )
    EMBEDDING_DIMENSION: int = Field(
        default=1536,
        description="Dimensionality of embedding vectors.",
    )

    # --- Thresholds ---
    DEDUP_SIMILARITY_THRESHOLD: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Cosine similarity above which an ingested fact is treated as a duplicate.",
    )
    HOT_CONSOLIDATION_THRESHOLD: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="importance_score above which consolidation runs immediately.",
    )

    # --- PostgreSQL ---
    POSTGRES_DSN: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/memory_sdk",
        description="Asyncpg connection string for PostgreSQL backends.",
    )

    # --- Qdrant ---
    QDRANT_URL: str = Field(
        default="http://localhost:6333",
        description="HTTP URL for the Qdrant service.",
    )
    QDRANT_API_KEY: str = Field(
        default="",
        description="API key for authenticated Qdrant instances (leave blank if unauthenticated).",
    )
    QDRANT_COLLECTION: str = Field(
        default="memory_archive",
        description="Name of the Qdrant collection used for the Deep Archive.",
    )

    # --- Local JSON substrate ---
    LOCAL_JSON_DIR: str = Field(
        default=".memory_state",
        description="Directory path where local_json substrate files are stored.",
    )


# Singleton — import this rather than instantiating MemoryConfig directly.
settings = MemoryConfig()
