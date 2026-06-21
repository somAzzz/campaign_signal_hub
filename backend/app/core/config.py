from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CSH_")

    app_name: str = "Campaign Signal Hub"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    sglang_base_url: str = "http://localhost:30000"
    sglang_model: str = "Qwen/Qwen3.5-35B-A3B"
    llm_provider: str = "sglang"
    llm_timeout_seconds: int = 120
    llm_max_tokens: int = 3072
    llm_batch_comments: int = 16


settings = Settings()
