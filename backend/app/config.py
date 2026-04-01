from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "SecureDiff"
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/icrrg_dev"
    REDIS_URL: str = "redis://localhost:6379/0"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://openrouter.ai/api/v1"
    REVIEW_MODEL: str = "nvidia/nemotron-3-super-120b-a12b:free"
    LLM_PROVIDER: str = "openai"  # "openai" or "mock"
    SECRET_KEY: str = "change-me"
    CORS_ORIGINS: list[str] = ["http://localhost:4200"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
