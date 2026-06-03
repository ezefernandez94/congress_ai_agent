from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/conference_bot"

    # Telegram
    telegram_bot_token: str = ""
    telegram_allowed_user_id: int = 0

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"

    # OpenAI (Whisper)
    openai_api_key: str = ""

    # Enrichment
    proxycurl_api_key: str = ""
    tavily_api_key: str = ""

    # App
    app_env: str = "development"
    webhook_secret: str = "changeme"
    base_url: str = "http://localhost:8000"

    # Optional
    apollo_api_key: str = ""
    timezone: str = "America/Los_Angeles"
    digest_hour: int = 7
    digest_minute: int = 30

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
