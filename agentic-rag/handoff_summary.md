# Handoff Summary - rag-chatbox

## 1. Project goal

`rag-chatbox` là FastAPI microservice cho chatbot RAG nội bộ của hệ thống Face Attendance/HR. Mục tiêu: ingest tài liệu chính sách/nội quy tiếng Việt, index vào Qdrant bằng BGE-M3 dense+sparse embeddings, retrieve/rerank context theo quyền truy cập, rồi trả lời bằng Gemini kèm citations.

## 2. Current architecture

Entrypoint: `run.py` chạy `src.main:app`.

Startup lifespan trong `src/main.py`:
- tạo Redis async client và ping
- load/warmup `EmbeddingClient` + `EmbeddingService`
- ensure Qdrant collection, tạo `QdrantVectorStore`
- load/warmup `RerankerClient` + `RerankerService`
- build `IngestionPipeline`
- tạo `APIServiceClient` trỏ tới attendance/api-service
- lưu services vào `app.state`

HTTP:
- `GET /health`
- `POST /api/v1/chat/message`
- `POST /api/v1/rag/documents`
- API auth qua header `X-API-Key`

Ingestion flow:
`UploadFile + metadata -> LoaderFactory -> PDF/DOCX/TXT loader -> LegalStructureAwareChunker -> DocumentIndexer -> EmbeddingService -> QdrantVectorStore`

Retrieval/chat flow intended:
`ChatService -> RetrievalPipeline -> HybridRetriever -> Qdrant hybrid RRF search -> RerankerService -> ContextBuilder -> GeminiClient`

Agentic layer is only partially present: `AgentState`, `ToolRegistry`, `VectorSearchTool`, `DatabaseQueryTool`, and `AskUserTool` exist, but `supervisor.py`, `planner.py`, `executor.py`, and routing modules are empty.

## 3. Files changed

This handoff update changed:
- `handoff_summary.md`

Pre-existing dirty/untracked files observed:
- `../attendance_service/app/main.py`
- `src/agents/state.py`
- `src/features/chat/schemas.py`
- `src/integrations/api_service/clients.py`
- `src/integrations/llm/prompts.py`
- `src/rag/retrieval/context_builder.py`
- `src/rag/retrieval/retrieval_pipeline.py`
- `src/tools/database_query_tool.py`
- `src/tools/registry.py`
- `src/rag/retrieval/schemas.py` untracked
- `src/tools/ask_user_tool.py` untracked

## 4. Public interfaces da chot

HTTP:
- `POST /api/v1/rag/documents`
  - multipart form: `document_id`, `filename`, `file_path`, `allowed_roles`, `file`
  - returns `DocumentIngestResponse`
- `POST /api/v1/chat/message`
  - body: `ChatRequest(message, employee_id, role, conversation_id, chat_history=[])`
  - returns `ChatResponse(answer, citations, low_confidence, used_context, ask_user, options, allow_free_text)`
- Auth: `X-API-Key`, checked by `verify_api_key`.

Internal:
- `IngestionPipeline.ingestion(...) -> IngestionResult`
- `LoaderFactory.load(...) -> list[Document]`
- `LegalStructureAwareChunker.chunk(...) -> list[DocumentChunk]`
- `DocumentIndexer.index_chunks(...) -> int`
- `RetrievalPipeline.retrieve_context(...) -> RetrievalPipelineResult`
- `APIServiceClient.get_employee/get_employee_current_shift/list_attendance_records`
- Tool names: `vector_search`, `database_query`, `ask_user`

## 5. Decisions made

- Use BGE-M3 for dense and sparse vectors.
- Use Qdrant named vectors and server-side RRF hybrid search.
- Apply document ACL filtering in Qdrant query via `allowed_roles`.
- Use BGE reranker after hybrid retrieval.
- Use single-worker executors for embedding/reranker model calls because model inference is treated as not thread-safe.
- Vietnamese policy/legal chunking uses section -> clause/khoan -> point/diem -> recursive fallback.
- Chunk IDs are deterministic UUID v5 for idempotent upsert.
- Prompts and observations are Vietnamese.
- Agent/tool runtime is being introduced, but direct RAG chat path is still wired in `ChatService`.

## 6. Known bugs/TODO

- `ChatService` imports `RAG_SYSTEM_PROMPT` and calls `PromptBuilder.build_rag_prompt`, but current `prompts.py` only defines `REACT_SYSTEM_PROMPT`, `build_system_prompt`, `build_react_prompt`, and `build_scratchpad`.
- `redis_client.py` references `settings.redis_db_session` and `settings.redis_session_url`, not defined in `Settings`.
- `QdrantClientManager.ensure_default_collections()` references `settings.qdrant_collection_law`, not defined.
- `requirements.txt` appears to miss `redis` although code imports `redis.asyncio` and `redis.exceptions`.
- `supervisor.py`, `planner.py`, `executor.py`, routing modules, web search, guardrails, and observability modules are empty placeholders.
- No real test source files in `tests/`; only cached bytecode was present.
- Import smoke check failed in current Python env because `fastapi` is not installed.
- `requirements.txt` contains several conda-local `file://...` pins, reducing portability.

## 7. Next task

Fix startup/import blockers first:
1. Align prompt API: either restore RAG prompt functions/constants or fully wire ReAct supervisor path.
2. Fix Redis settings/client and add `redis` dependency.
3. Remove or define `qdrant_collection_law`.
4. Install dependencies in the active environment and run import/startup smoke check.
5. Add focused tests for `ContextBuilder`, `LegalStructureAwareChunker`, `RetrievalPipeline`, and tool formatting.
