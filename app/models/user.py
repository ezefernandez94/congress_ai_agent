import uuid

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class BotUser(Base, TimestampMixin):
    """A Telegram user allowed to talk to the bot.

    This table is the source of truth for both access and per-user
    preferences. TELEGRAM_ALLOWED_USER_IDS only bootstraps owners, who are
    seeded here on first contact and can never be locked out by bad data.
    """

    __tablename__ = "bot_users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    receives_digest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
