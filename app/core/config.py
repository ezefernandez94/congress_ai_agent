import hashlib

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/conference_bot"

    # Telegram
    telegram_bot_token: str = ""
    telegram_allowed_user_id: int = 0          # legacy single-user var (still honoured)
    telegram_allowed_user_ids: str = ""        # comma-separated list, e.g. "123,456"

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

    # Injected by Railway once the service has a generated public domain.
    # Preferred over BASE_URL in production so the hostname is never hand-typed.
    railway_public_domain: str = ""

    # Web frontend
    web_session_secret: str = ""     # signs the browser session cookie
    telegram_bot_username: str = ""  # without the @ — required by the login widget

    # Optional
    apollo_api_key: str = ""
    timezone: str = "America/Los_Angeles"
    digest_hour: int = 7
    digest_minute: int = 30

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_database_url_scheme(cls, v: str) -> str:
        """
        Railway provides DATABASE_URL as postgresql:// but SQLAlchemy
        requires postgresql+asyncpg:// for the asyncpg driver.
        Rewrite any bare postgresql:// or postgres:// scheme automatically.
        """
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("railway_public_domain", "base_url", mode="before")
    @classmethod
    def strip_url_noise(cls, v: str) -> str:
        """Tolerate a pasted scheme or trailing slash in either value."""
        return (v or "").strip().rstrip("/")

    @property
    def public_base_url(self) -> str:
        """Base URL Telegram should call back on.

        RAILWAY_PUBLIC_DOMAIN is a bare hostname (no scheme) and only exists
        once a public domain has been generated for the service, so BASE_URL
        stays the fallback for local development.
        """
        if self.railway_public_domain:
            domain = self.railway_public_domain.removeprefix("https://").removeprefix("http://")
            return f"https://{domain}"
        return self.base_url

    @property
    def webhook_url(self) -> str:
        return f"{self.public_base_url}/webhook/{self.webhook_secret}"

    @property
    def allowed_user_ids(self) -> set[int]:
        """
        Every Telegram user ID permitted to talk to the bot.
        Merges the legacy TELEGRAM_ALLOWED_USER_ID with the comma-separated
        TELEGRAM_ALLOWED_USER_IDS so existing deployments keep working.
        """
        ids: set[int] = set()
        if self.telegram_allowed_user_id:
            ids.add(self.telegram_allowed_user_id)
        for chunk in self.telegram_allowed_user_ids.split(","):
            chunk = chunk.strip()
            if chunk:
                ids.add(int(chunk))
        return ids

    def is_allowed_user(self, user_id: int) -> bool:
        return user_id in self.allowed_user_ids

    @property
    def session_secret(self) -> str:
        """Key used to sign the web session cookie.

        Falls back to a value derived from the bot token so an existing
        deployment keeps working without a new env var, at the cost of
        invalidating every session if the token is ever rotated. Set
        WEB_SESSION_SECRET explicitly in production.
        """
        if self.web_session_secret:
            return self.web_session_secret
        return hashlib.sha256(
            f"web-session:{self.telegram_bot_token or self.webhook_secret}".encode()
        ).hexdigest()

    @property
    def login_widget_ready(self) -> bool:
        """Whether the Telegram Login Widget can actually be rendered."""
        return bool(self.telegram_bot_username and self.telegram_bot_token)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
