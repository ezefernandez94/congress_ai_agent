from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import BotUser
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[BotUser]):
    def __init__(self, db: AsyncSession):
        super().__init__(BotUser, db)

    async def get_by_telegram_id(self, telegram_user_id: int) -> BotUser | None:
        result = await self.db.execute(
            select(BotUser).where(BotUser.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[BotUser]:
        result = await self.db.execute(select(BotUser).order_by(BotUser.created_at))
        return list(result.scalars().all())

    async def first_owner(self) -> BotUser | None:
        """The earliest active owner — the identity the dev-mode web bypass assumes."""
        result = await self.db.execute(
            select(BotUser)
            .where(BotUser.is_owner.is_(True), BotUser.is_active.is_(True))
            .order_by(BotUser.created_at)
            .limit(1)
        )
        return result.scalars().first()

    async def list_digest_recipients(self) -> list[BotUser]:
        result = await self.db.execute(
            select(BotUser)
            .where(BotUser.is_active.is_(True), BotUser.receives_digest.is_(True))
            .order_by(BotUser.created_at)
        )
        return list(result.scalars().all())

    async def ensure_user(
        self,
        telegram_user_id: int,
        *,
        display_name: str | None = None,
        is_owner: bool = False,
    ) -> BotUser:
        """Get the user, creating them if absent. Idempotent — safe per message."""
        user = await self.get_by_telegram_id(telegram_user_id)
        if user is None:
            return await self.create(
                {
                    "telegram_user_id": telegram_user_id,
                    "display_name": display_name,
                    "is_owner": is_owner,
                    "is_active": True,
                    "receives_digest": True,
                }
            )

        # Backfill a name we didn't have, and never demote an env-listed owner.
        changed = False
        if display_name and not user.display_name:
            user.display_name = display_name
            changed = True
        if is_owner and not user.is_owner:
            user.is_owner = True
            changed = True
        if changed:
            self.db.add(user)
            await self.db.flush()
        return user

    async def set_digest_preference(self, telegram_user_id: int, enabled: bool) -> BotUser | None:
        user = await self.get_by_telegram_id(telegram_user_id)
        if user is None:
            return None
        user.receives_digest = enabled
        self.db.add(user)
        await self.db.flush()
        return user

    async def set_active(self, telegram_user_id: int, active: bool) -> BotUser | None:
        user = await self.get_by_telegram_id(telegram_user_id)
        if user is None:
            return None
        user.is_active = active
        self.db.add(user)
        await self.db.flush()
        return user
