import asyncio
from datetime import datetime, timezone
from sqlalchemy import delete
from core.database import async_session
from core.logger import get_logger
from models.password_reset import PasswordReset
from services.email_service import send_pending_emails

log = get_logger(__name__)


class EmailWorker:
    def __init__(self, interval: int = 30):
        self.interval = interval

    async def run(self) -> None:
        log.info("Email worker started", interval=self.interval)
        cycle = 0
        while True:
            try:
                async with async_session() as db:
                    sent_count = await send_pending_emails(db)
                    if sent_count:
                        log.info("Queued emails sent", count=sent_count)
                if cycle % 120 == 0:
                    await self._cleanup_expired_tokens()
                cycle += 1
            except asyncio.CancelledError:
                log.info("Email worker cancelled")
                break
            except Exception as exc:
                log.error("Email worker error", error=str(exc))
            await asyncio.sleep(self.interval)

    async def _cleanup_expired_tokens(self) -> None:
        async with async_session() as db:
            await db.execute(
                delete(PasswordReset).where(
                    PasswordReset.expires_at < datetime.now(timezone.utc),
                    PasswordReset.used.is_(False),
                )
            )
            await db.commit()
            log.info("expired_reset_tokens_cleaned")
