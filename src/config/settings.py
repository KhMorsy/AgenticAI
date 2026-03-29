from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    scraping_rate_limit: int = 10
    newsletter_schedule: str = "daily"
    output_dir: str = "./output"
    log_level: str = "INFO"

    model_config = {
        "env_prefix": "AGENTIC_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }
