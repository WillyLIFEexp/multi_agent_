"""Application settings loaded from environment variables."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration, populated from the environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "multi_agent"
    version: str = "0.1.0"
    environment: str = Field(default="development")
    debug: bool = Field(default=True)

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./app.db")

    # MongoDB (persistent chat memory + LangGraph checkpointer)
    mongodb_url: str = Field(default="mongodb://localhost:27017")
    mongodb_db_name: str = Field(default="multi_agent")
    mongodb_history_collection: str = Field(default="chat_history")
    # Optional TTL (seconds) for checkpoint documents; None keeps them forever.
    mongodb_checkpoint_ttl: int | None = Field(default=None)

    # LLM / agents
    llm_provider: str = Field(default="openai")  # openai | azure | ollama
    default_model: str = Field(default="gpt-4o-mini")
    temperature: float = Field(default=0.0)

    # OpenAI
    openai_api_key: str | None = Field(default=None)

    # Azure OpenAI
    azure_openai_api_key: str | None = Field(default=None)
    azure_openai_endpoint: str | None = Field(default=None)
    azure_openai_deployment: str | None = Field(default=None)
    azure_openai_api_version: str = Field(default="2024-10-21")

    # Local Ollama
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.1")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
