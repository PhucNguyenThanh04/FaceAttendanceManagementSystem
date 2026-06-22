from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # LLM
    google_api_key: str
    gemini_model: str = "gemini-1.5-flash"
    llm_temperature: float = 0.1
    llm_max_output_tokens: int = 2048
    llm_timeout: float = 30.0

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_policy: str 
    qdrant_timeout: float = 5.0
    qdrant_upsert_batch_size: int

    redis_host: str
    redis_port: int
    redis_password: str = ""
    redis_url: str

    dense_vector_name: str
    sparse_vector_name: str
    bge_m3_dense_size: int

    # Embedding / reranking
    embedding_model: str 
    embedding_device: str

    reranker_model: str 
    reranker_device: str
    retrieval_top_k: int
    rerank_top_n: int
    retrieval_score_threshold: float

    # API server
    api_host: str
    api_port: int
    api_debug: bool

    # Optional web search
    tavily_api_key: str | None = None
    web_search_max_results: int = 5

    # Backward-compatible optional fields for future internal-service wiring.
    api_server_base_url: str = ""
    api_key: str = ""
    agent_server_name: str = "rag-chatbox"

    @property
    def host_qdrant(self) -> str:
        return self.qdrant_host

    @property
    def port_qdrant(self) -> int:
        return self.qdrant_port

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    @property
    def url_qdrant(self) -> str:
        return self.qdrant_url

    @property
    def default_qdrant_collection(self) -> str:
        return self.qdrant_collection_policy

    @property
    def qdrant_collection_name(self) -> str:
        return self.default_qdrant_collection

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

    



if __name__ == "__main__":
    # Test load settings
    settings = get_settings()
    print("Gemini Model:", settings.gemini_model)
    print("Qdrant URL:", settings.qdrant_url)
    print("Policy Collection:", settings.qdrant_collection_policy)
    print("Embedding Model:", settings.embedding_model)
    print("API:", f"{settings.api_host}:{settings.api_port}")
