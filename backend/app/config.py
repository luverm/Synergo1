from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_base_url: str = "http://ollama:11434"
    llm_model: str = "llama3.2:3b"
    embedding_model: str = "nomic-embed-text"

    chroma_path: str = "/data/chroma"
    documents_path: str = "/data/documents"

    api_key: str = ""
    allowed_origins: str = "http://localhost:8501"

    max_upload_mb: int = 25
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 4
    request_timeout_s: float = 600.0


settings = Settings()
