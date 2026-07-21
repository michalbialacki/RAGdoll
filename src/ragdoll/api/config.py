"""App-wide settings, loaded from environment variables (.env in local dev)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RAGDOLL_")

    aws_region: str = "eu-central-1"
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "ragdoll_chunks"
