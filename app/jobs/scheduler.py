from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.logging import logger

_scheduler: AsyncIOScheduler | None = None


async def start_scheduler() -> None:
    global _scheduler
    from app.jobs.daily_digest import send_daily_digest

    _scheduler = AsyncIOScheduler(timezone=settings.timezone)
    _scheduler.add_job(
        func=send_daily_digest,
        trigger=CronTrigger(hour=settings.digest_hour, minute=settings.digest_minute),
        id="daily_digest",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "scheduler_started",
        digest_time=f"{settings.digest_hour:02d}:{settings.digest_minute:02d}",
        timezone=settings.timezone,
    )


async def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")
