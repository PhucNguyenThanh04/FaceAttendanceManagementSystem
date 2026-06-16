# Handoff Summary — RAG Chatbox

## 1. Project Goal
Agentic RAG chatbot for HR/attendance management (Vietnamese). Built with FastAPI + Gemini 1.5 Flash + Qdrant (BGE-M3 hybrid embeddings). Part of `FaceAttendanceManagementSystem` monorepo.

**Workspace:** `/home/thanh-phuc/PycharmProjects/FaceAttendanceManagementSystem/rag-chatbox/`

## 2. Current Architecture

```
Ingestion (✅ DONE):
  Upload → LoaderFactory → LegalStructureAwareChunker → DocumentIndexer → Qdrant

Query-time (IN PROGRESS):
  Query → HybridRetriever → [Reranker] → [ContextBuilder] → [PromptBuilder] → [GeminiClient] → Answer
                ✅              ❌            ❌               ✅ exists         ✅ exists
```

**Key design decisions made this session:**
- **AsyncQdrantClient** — all Qdrant interactions are native async (no `asyncio.to_thread`)
- **Post-filter permissions** — retrieve ALL chunks first (no role filter), rerank, THEN check `allowed_roles`. If best chunk is not accessible → tell user "không có quyền" instead of giving wrong answer from a less-relevant chunk
- **Reranker will follow same pattern as Embedding** — sync model inference in `ThreadPoolExecutor`, wrapped by async service layer

## 3. Files Changed This Session

| File | Change |
|---|---|
| `integrations/qdrant/client.py` | `QdrantClient` → `AsyncQdrantClient`, all methods async, added `close()` |
| `integrations/qdrant/store.py` | All methods async. Removed: `upsert_chunks`, `_build_point`, `_search_hybrid_fallback`, `_rrf_merge`, `_slice_sparse_vectors`, `_validate_vector_lengths`, `_point_id`, `payload` field from `QdrantSearchResult`. Simplified `search_hybrid` to call `query_points` directly (RRF server-side) |
| `rag/ingestion/indexer.py` | `_upsert_in_batches` → async, removed `asyncio.to_thread` from `delete_document` |
| `rag/ingestion/pipeline.py` | `ensure_collection` call → `await` |
| `main.py` | `await ensure_collection`, store `qdrant_manager` on `app.state`, `await close()` on shutdown |
| `rag/retrieval/hybrid_retriever.py` | **NEW** — `HybridRetriever.retrieve(query, collection, top_k)` — no `allowed_role` param |

## 4. Public Interfaces Finalized

```python
# HybridRetriever — rag/retrieval/hybrid_retriever.py
async def retrieve(query: str, collection_name: str | None, top_k: int | None) -> list[QdrantSearchResult]

# QdrantSearchResult — integrations/qdrant/store.py
@dataclass
class QdrantSearchResult:
    point_id: str
    score: float
    content: str
    metadata: dict[str, Any]  # contains allowed_roles, filename, clause_number, etc.

# QdrantVectorStore — async methods:
async def upsert_points(collection_name, points, wait) -> int
async def search_dense(collection_name, query_vector, top_k, allowed_role, metadata_filter) -> list[QdrantSearchResult]
async def search_hybrid(collection_name, dense_query_vector, sparse_query_vector, top_k, ...) -> list[QdrantSearchResult]
async def delete_by_document_id(collection_name, document_id, wait) -> None

# QdrantClientManager — async methods:
async def ensure_collection(collection_name) -> None
async def close() -> None
```

## 5. Decisions Made

1. **No pre-filter by role at retrieval** — permission check happens post-rerank in ContextBuilder/guardrails
2. **Removed SDK compatibility fallbacks** — `qdrant-client==1.9.1` is pinned, no need for `hasattr` guards
3. **RRF runs server-side** via `models.FusionQuery(fusion=models.Fusion.RRF)` — removed manual `_rrf_merge`
4. **`vector_retriever.py` is redundant** — `HybridRetriever` already falls back to dense-only when `sparse=None`. User may want to delete it
5. **Incremental coding rules** — user requires plan-before-code, one step at a time, no auto-completing modules
6. **Reranker pattern** — will use `ThreadPoolExecutor` like `EmbeddingClient` (sync model, async wrapper)

## 6. Known Bugs / TODO

- `client.py` (`GeminiClient._call_once`) — missing generic `Exception` catch (unlike `generate_stream` which has it). Should add for production safety
- `vector_retriever.py` — empty file, user agreed it's redundant but hasn't deleted yet
- LangChain/LangGraph in `requirements.txt` but unused — dead dependencies

## 7. Next Task — Implementation Plan

**Agreed pipeline (user confirmed):**

```
Top-20 chunks (HybridRetriever ✅)
  → 1. RERANK (reranker.py) ← NEXT
  → 2. FILTER (permission check post-rerank)
  → 3. CONTEXT WINDOW MANAGEMENT
  → 4. PROMPT ENGINEERING (prompts.py ✅)
  → 5. GENERATE (client.py ✅)
  → 6. GROUNDING CHECK
  → ANSWER + CITATIONS
```

**Immediate next step:** Write `Reranker` in `src/rag/retrieval/reranker.py`
- Cross-encoder model: `cross-encoder/ms-marco-MiniLM-L-6-v2` (already in settings)
- Pattern: sync inference in `ThreadPoolExecutor`, async wrapper
- Input: `query + list[QdrantSearchResult]` → Output: `list[QdrantSearchResult]` reranked
