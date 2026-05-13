# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Commands

```bash
uv run main.py          # Run entry point
uv run pytest           # Run tests
uv run ruff check .     # Lint
uv run ruff format .    # Format
uv add <package>        # Add a dependency
```

No test or lint tooling is configured yet — add `pytest`, `ruff`, and required runtime packages to `pyproject.toml` via `uv add` before using the commands above.

## Architecture: Two-Brain Memory System

This SDK implements a dual-storage architecture for autonomous AI agent memory:

### Camp 1 — Deep Archive (`core/archive.py`)
Immutable vector ledger storing exact, high-fidelity interaction histories. Backed by **PostgreSQL + pgvector** (primary) or **Qdrant** (fallback). Every stored record must include `memory_id`, `user_id`, `timestamp`, `session_id`, and `importance_score` metadata.

Key invariants:
- Skip insertion if semantic similarity to an existing record exceeds **0.95**
- `hybrid_search()` returns exact detailed chunks — never summaries
- Hybrid search combines dense semantic search with sparse BM25/full-text search

### Camp 2 — Active Substrate (`core/substrate.py`)
Mutable, sectioned Markdown state backed by JSON. Keys are Markdown section headers; values are detailed text blocks. Supports targeted retrieval (`get_sections`), full overwrite (`update_section`), and append (`append_to_section`).

### Consolidation Worker (`core/worker.py`)
Async background engine that runs after sessions end or immediately when `importance_score > 0.85`. Pipeline order:
1. **Coreference resolution** — rewrite pronouns to explicit entities
2. **Conflict detection** — read-before-write against Substrate; emit `update_section` on contradiction
3. **Extraction** — preserve exact technical phrasing, variable names, tracebacks, code blocks; emit to `archive.ingest()`

The worker must define a `EXTRACTION_SYSTEM_PROMPT` constant instructing the LLM never to summarize.

### Storage Layer (`storage/`)
- `base.py` — `BaseVectorStore` and `BaseStateStore` ABCs that all backends must implement
- `postgres_store.py` — pgvector archive + JSONB substrate
- `qdrant_store.py` — Qdrant archive fallback

Core logic must depend only on the ABCs, never on a specific driver.

### Public Entry Point (`client.py`)
`MemoryClient` is the single public interface. Its methods accept a `user_id` string (the SDK does not manage auth — the caller authenticates). Key async methods: `ingest()`, `search()`, `get_state()`.

### Configuration (`config.py`)
Loads from `.env`. Required fields:

| Field | Values |
|---|---|
| `RUN_MODE` | `'local'` (bypass isolation) / `'server'` (strict `user_id` filtering) |
| `VECTOR_DB_TYPE` | `'pgvector'` / `'qdrant'` |
| `STATE_DB_TYPE` | `'postgresql'` / `'local_json'` |
| `HYBRID_SEARCH_ENABLED` | boolean |

### Schemas (`schemas.py`)
Pydantic models: `MemoryPayload` (raw transcript input), `ExtractedFact` (worker output with `fact_text`, `importance_score`, `timestamp`), `SubstrateSection`, `SearchQuery` (with `dense_weight`, `sparse_weight`, temporal filters).

### Integration Wrappers (`integrations/agent_tools.py`)
LangGraph / OpenAI-schema tool wrappers: `Search_Personal_History(query, date_filter)` → `archive.hybrid_search()`, `Delete_Memory(memory_id)` → archive deletion.

## Critical Constraints

- **No synchronous LLM calls in the core loop** — all consolidation is async
- **Strict dependency injection** — never couple core logic to a specific DB driver
- All ingestion is async; search must support pagination
- Archive failures must not corrupt substrate state
- All public SDK methods require docstrings and type hints
- The SDK does not implement OAuth or manage sessions — it is a downstream consumer

## Development Behaviors & Rules

- **Incremental Implementation:** Do not attempt to write the entire SDK at once. Build and test one phase at a time based on the user's instructions.
- **Mock First, Connect Later:** When building the LLM Consolidation Worker (`worker.py`), start by defining the prompt and input/output structure with a mocked LLM response before wiring up the actual API calls.
- **Logging over Printing:** NEVER use `print()`. Use Python's built-in `logging` module configured at the `INFO` level for all system tracking.
- **Environment Management:** Always generate a `.env.example` file alongside `config.py` so the expected environment variables are documented.
- **Type Checking:** Every function MUST have strict type hints.