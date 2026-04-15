import asyncio
from datetime import datetime, timezone
from uuid import UUID
import smtplib
from email.mime.text import MIMEText
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import get_settings
from core.logger import get_logger
from models.email_queue import EmailQueue

log = get_logger(__name__)
settings = get_settings()


def _smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD and settings.SMTP_FROM)


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


def _send_email(to_email: str, subject: str, body: str) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


async def send_pending_emails(db: AsyncSession, batch_size: int = 20) -> int:
    if not _smtp_configured():
        return 0

    result = await db.execute(
        select(EmailQueue).where(EmailQueue.sent.is_(False)).order_by(EmailQueue.created_at.asc()).limit(batch_size)
    )
    pending = result.scalars().all()
    sent_count = 0

    for email in pending:
        try:
            await asyncio.to_thread(_send_email, email.to_email, email.subject, email.body)
            email.sent = True
            email.sent_at = datetime.now(timezone.utc)
            sent_count += 1
        except Exception as exc:
            log.error("Email send failed", to_email=email.to_email, error=str(exc))

    if pending:
        await db.commit()

    return sent_count
