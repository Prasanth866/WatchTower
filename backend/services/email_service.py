import asyncio
from datetime import datetime, timezone
from uuid import UUID
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import get_settings
from core.logger import get_logger
from models.email_queue import EmailQueue

log = get_logger(__name__)
settings = get_settings()


def _resend_configured() -> bool:
    return bool(settings.RESEND_API_KEY and settings.RESEND_FROM_EMAIL)


async def queue_alert_email(
    db: AsyncSession,
    user_id: UUID,
    to_email: str,
    subject: str,
    body: str,
) -> None:
    queued = EmailQueue(
        user_id=user_id,
        to_email=to_email,
        subject=subject,
        body=body,
        sent=False,
    )
    db.add(queued)


async def _send_email_async(client: httpx.AsyncClient, to_email: str, subject: str, body: str) -> None:
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": subject,
        "text": body,
    }
    response = await client.post(url, json=payload, headers=headers)
    response.raise_for_status()


async def send_pending_emails(db: AsyncSession, batch_size: int = 20) -> int:
    if not _resend_configured():
        log.warning("Resend service is not configured. Skipping email queue dispatch.")
        return 0

    result = await db.execute(
        select(EmailQueue).where(EmailQueue.sent.is_(False)).order_by(EmailQueue.created_at.asc()).limit(batch_size)
    )
    pending = result.scalars().all()
    if not pending:
        return 0

    async with httpx.AsyncClient(timeout=10.0) as client:
        async def send_one(email: EmailQueue) -> bool:
            try:
                await _send_email_async(client, email.to_email, email.subject, email.body)
                email.sent = True
                email.sent_at = datetime.now(timezone.utc)
                return True
            except Exception as exc:
                log.error("Resend HTTP email send failed", to_email=email.to_email, error=str(exc))
                return False

        results = await asyncio.gather(*(send_one(email) for email in pending), return_exceptions=True)
        sent_count = sum(1 for res in results if res is True)

    await db.commit()
    return sent_count
