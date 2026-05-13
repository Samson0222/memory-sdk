# Memory System Implementation Blueprint

**Target Audience:** Autonomous Coding Agent (Claude Code)  
**Project Type:** Decoupled Python SDK for a "Two-Brain" AI Agent Memory System  
**Package Manager:** `uv`

---

## 1. Architectural Mandate

You are tasked with building a robust, decoupled Memory SDK. This system uses a "Two-Brain" architecture:

1. **Camp 1 (The Deep Archive):** An immutable vector ledger storing exact, high-detail interaction histories.
2. **Camp 2 (The Active Substrate):** A highly mutable, sectioned Markdown state (backed by JSON) that tracks the user's immediate operational reality.

### CRITICAL RULES

- **No Synchronous LLM Calls in Core Loop:** All memory consolidation, coreference resolution, and ingestion MUST happen asynchronously in a background worker.
- **Strict Dependency Injection:** Storage backends must inherit from abstract base classes. Do not tightly couple core logic to a specific database driver.
- **Configuration Driven:** All major features (Vector DB type, run modes, search weights) must be controllable via a central `config.py`.

---

## 2. Directory Structure

```text
memory_sdk/
├── __init__.py
├── config.py                 # Central configuration and toggles
├── client.py                 # Main MemoryClient entry point
├── schemas.py                # Pydantic models for data validation
├── core/
│   ├── substrate.py          # Camp 2: Active State management (JSON-backed Markdown)
│   ├── archive.py            # Camp 1: Deep Archive management (pgvector/Qdrant)
│   └── worker.py             # Asynchronous Consolidation Worker (Coreference, Extraction)
├── storage/
│   ├── base.py               # Abstract Base Classes (BaseVectorStore, BaseStateStore)
│   ├── postgres_store.py     # Implements JSONB state and pgvector archive
│   └── qdrant_store.py       # Fallback implementation for existing RAG infrastructure
└── integrations/
    └── agent_tools.py        # LangGraph/OpenAI schema tool wrappers for the SDK
```

---

## 3. Data Structures & Schemas (`schemas.py`)

Use `pydantic` for strict data validation.

### `MemoryPayload`

The raw chat transcript input.

### `ExtractedFact`

The output from the background worker.

Required fields:

- `fact_text`
  - Resolved pronouns
  - Detailed phrasing
- `importance_score`
  - Float between `0.0` and `1.0`
- `timestamp`

### `SubstrateSection`

Key-value pairing for the Markdown hybrid state.

Example:

```python
section_header: "string content"
```

### `SearchQuery`

Parameters for Hybrid Search.

Fields:

- `query`
- `dense_weight`
- `sparse_weight`
- temporal filters

---

## 4. Component Specifications

### 4.1 The Command Center (`config.py`)

Implement a configuration class that loads from `.env`.

#### Required Configuration Fields

##### `RUN_MODE`

Controls execution isolation behavior.

Options:

- `'local'`
  - Bypass OAuth/isolation
- `'server'`
  - Strict `user_id` filtering

##### `VECTOR_DB_TYPE`

Supported values:

- `'pgvector'`
- `'qdrant'`

##### `STATE_DB_TYPE`

Supported values:

- `'postgresql'`
- `'local_json'`

##### `HYBRID_SEARCH_ENABLED`

Boolean flag controlling hybrid retrieval behavior.

---

### 4.2 The Active Substrate (`core/substrate.py`)

#### Storage Design

Use segmented JSON storage.

Keys act as Markdown headers.

Example:

```markdown
## Active Stack
```

Values are detailed text blocks.

#### Required Methods

##### `get_sections(user_id, section_names=[])`

Retrieves targeted sections for context window injection.

##### `update_section(user_id, section_name, content)`

Overwrites a specific section.

##### `append_to_section(user_id, section_name, content)`

Appends data to an existing section.

---

### 4.3 The Deep Archive (`core/archive.py`)

#### Storage Backend

Vector database with metadata filtering support.

#### Metadata Schema

Each memory entry must contain:

- `memory_id`
- `user_id`
- `timestamp`
- `session_id`
- `importance_score`

#### Required Methods

##### `ingest(user_id, extracted_facts[])`

Responsibilities:

- Upsert extracted facts
- Prevent duplication bloat
- Perform semantic similarity checks before insertion

Deduplication rule:

```text
Skip insertion if semantic similarity > 0.95
```

##### `hybrid_search(user_id, query, top_k)`

Executes combined retrieval:

- Dense semantic search
- Sparse BM25 / keyword search

Returns:

- Exact detailed chunks
- Not summaries

---

### 4.4 The Consolidation Worker (`core/worker.py`)

This component is the reconciliation engine.

Implement an asynchronous class:

```python
class ConsolidationWorker:
    ...
```

#### Trigger 1 — End of Session

Processes bulk chat logs after a session completes.

#### Trigger 2 — Hot Consolidation

Immediately triggers if:

```text
importance_score > 0.85
```

Required System Prompting Rules for Worker:
The worker.py must contain a strictly defined system prompt constant for the extraction LLM. It MUST explicitly command: "You are a high-fidelity memory extractor. You must preserve the exact technical phrasing, variable names, tracebacks, and code blocks. Never generate high-level summaries. Extract the precise details."

#### Pipeline Execution Order

##### 1. Coreference Resolution

Rewrite raw text into explicit entities.

Example:

```text
"He changed the stack"
↓
"John changed the backend stack from Flask to FastAPI"
```

##### 2. Conflict Detection (Read-Before-Write)

Compare new facts against existing Substrate JSON blocks.

If contradictions are detected:

- Emit an `update_section` command
- Replace outdated operational state

Example contradiction:

```text
Old state: PostgreSQL
New state: Supabase
```

##### 3. Detailed Extraction

Rules:

- Do NOT summarize
- Preserve implementation details
- Preserve technical wording
- Wrap code blocks in Markdown

Final output must be emitted to:

```python
archive.ingest()
```

---

### 4.5 Integration Wrappers (`integrations/agent_tools.py`)

Expose SDK functionality as agent-compatible tools for orchestrators such as LangGraph or OpenAI tool calling.

#### `Search_Personal_History`

```python
Search_Personal_History(
    query: str,
    date_filter: Optional[str]
)
```

Wraps:

```python
archive.hybrid_search()
```

#### `Delete_Memory`

```python
Delete_Memory(memory_id: str)
```

Wraps explicit archive deletion functionality.

---

## 5. Engineering Constraints

### Performance Requirements

- All ingestion must be asynchronous
- Search operations must support pagination
- Deduplication checks must happen before vector insertion
- Avoid blocking operations inside request lifecycle

### Reliability Requirements

- All storage implementations must be swappable
- Core logic must not depend directly on database vendors
- Failures in archive ingestion must not corrupt substrate state

### Maintainability Requirements

- Use typed interfaces everywhere
- Prefer composition over inheritance
- Keep orchestration logic separate from persistence logic
- All SDK public methods must contain docstrings and type hints

---

## 6. Recommended Tech Stack

### Core Framework

- Python 3.11+
- `uv`
- `pydantic`
- `asyncio`

### Vector Storage

Preferred:

- PostgreSQL + `pgvector`

Fallback:

- Qdrant

### Sparse Retrieval

Options:

- BM25
- PostgreSQL full-text search

### Embeddings

Use provider-agnostic interfaces.

Examples:

- OpenAI
- VoyageAI
- Instructor
- Local embedding models

---

## 7. Expected Deliverables

The coding agent should generate:

- Fully typed Python SDK
- Async-compatible architecture
- Pluggable storage layer
- Working hybrid retrieval pipeline
- Background consolidation worker
- Clean modular folder structure
- Environment-based configuration system
- Agent-tool integration wrappers
- Comprehensive docstrings
- Unit-test-ready architecture

---

## 8. Non-Goals

The SDK should NOT:

- Contain frontend code
- Depend directly on a single LLM provider
- Hardcode database implementations
- Execute synchronous memory consolidation
- Store summarized memory instead of detailed records
- Implement or manage the Web App OAuth flow. The SDK acts purely as a downstream consumer; it assumes the parent application (e.g., a FastAPI router) has already authenticated the user and will securely pass the user_id string into the client.py methods.

---

## 9. Final Instruction to Coding Agent

Prioritize:

1. Decoupling
2. Async architecture
3. Deterministic state management
4. High-fidelity memory preservation
5. Extensibility for future memory backends

The implementation should feel like infrastructure middleware, not application business logic.

## 10. Development & Implementation Phases

To ensure stability and prevent architectural spaghetti, this SDK must be built incrementally. Claude Code (or any autonomous agent) should execute these phases sequentially.

### Phase 1: Foundations (Schemas, Config, & Interfaces)
- **Goal:** Establish the strict typed boundaries.
- **Tasks:** - Install `pydantic`, `pydantic-settings`, and `python-dotenv` via `uv`.
  - Implement Pydantic models in `schemas.py`.
  - Implement environment loading in `config.py`.
  - Define Abstract Base Classes in `storage/base.py` (`BaseVectorStore`, `BaseStateStore`).

### Phase 2: Local Storage Fallbacks (Rapid Testing Layer)
- **Goal:** Build the storage mechanisms without requiring Docker or a live database.
- **Tasks:**
  - Implement `storage/local_json_store.py` (inherits `BaseStateStore`).
  - Implement a mock/in-memory vector store in `storage/qdrant_store.py` (inherits `BaseVectorStore`).

### Phase 3: The Core Engines
- **Goal:** Implement the business logic for the Two-Brain system.
- **Tasks:**
  - Build `core/substrate.py` utilizing the injected StateStore.
  - Build `core/archive.py` utilizing the injected VectorStore (ensure >0.95 semantic similarity deduplication check is stubbed).

### Phase 4: The Consolidation Worker
- **Goal:** Build the asynchronous LLM pipeline.
- **Tasks:**
  - Build `core/worker.py`.
  - Define the `EXTRACTION_SYSTEM_PROMPT` (Must explicitly ban summarization).
  - Implement the pipeline: Coreference Resolution → Conflict Detection → Detailed Extraction.
  - *Note: Mock the LLM API calls initially to test data flow.*

### Phase 5: Client API & Integration Wrappers
- **Goal:** Create the public entry points.
- **Tasks:**
  - Implement `client.py` (`MemoryClient`) linking config to the respective engines.
  - Implement `integrations/agent_tools.py` with LangGraph/OpenAI-compatible wrappers (`Search_Personal_History`, `Delete_Memory`).

### Phase 6: Production Database Integration
- **Goal:** Connect the real infrastructure.
- **Tasks:**
  - Add `asyncpg` and `pgvector` via `uv`.
  - Implement `storage/postgres_store.py` mapping to JSONB and pgvector.
  - Write a functional `demo.py` end-to-end integration test.