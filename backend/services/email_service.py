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

_EMAIL_SEND_CONCURRENCY = 5
_EMAIL_MAX_RETRIES = 2
_EMAIL_RETRY_DELAY = 1.0


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


_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


async def send_pending_emails(db: AsyncSession, batch_size: int = 20) -> int:
    if not _resend_configured():
        log.warning("Resend service is not configured. Skipping email queue dispatch.")
        return 0

    result = await db.execute(
        select(EmailQueue)
        .where(EmailQueue.sent.is_(False))
        .order_by(EmailQueue.created_at.asc())
        .limit(batch_size)
    )
    pending = result.scalars().all()
    if not pending:
        return 0

    semaphore = asyncio.Semaphore(_EMAIL_SEND_CONCURRENCY)

    async with httpx.AsyncClient(timeout=10.0) as client:
        async def send_one(email: EmailQueue) -> bool:
            async with semaphore:
                last_exc: Exception | None = None
                for attempt in range(1, _EMAIL_MAX_RETRIES + 1):
                    try:
                        await _send_email_async(client, email.to_email, email.subject, email.body)
                        email.sent = True
                        email.sent_at = datetime.now(timezone.utc)
                        return True
                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code in _TRANSIENT_STATUS_CODES:
                            last_exc = exc
                            retry_after = float(
                                exc.response.headers.get("Retry-After", _EMAIL_RETRY_DELAY * attempt)
                            )
                            log.warning(
                                "Resend transient error, retrying",
                                to_email=email.to_email,
                                status=exc.response.status_code,
                                attempt=attempt,
                                retry_after=retry_after,
                            )
                            await asyncio.sleep(retry_after)
                        else:
                            # Non-transient (e.g. 400 bad request) — don't retry
                            log.error(
                                "Resend non-transient error, skipping",
                                to_email=email.to_email,
                                status=exc.response.status_code,
                                error=str(exc),
                            )
                            return False
                    except (httpx.TimeoutException, httpx.ConnectError) as exc:
                        last_exc = exc
                        log.warning(
                            "Resend network error, retrying",
                            to_email=email.to_email,
                            attempt=attempt,
                            error=str(exc),
                        )
                        await asyncio.sleep(_EMAIL_RETRY_DELAY * attempt)
                    except Exception as exc:
                        log.error("Resend unexpected error", to_email=email.to_email, error=str(exc))
                        return False

                log.error(
                    "Resend failed after retries",
                    to_email=email.to_email,
                    error=str(last_exc),
                )
                return False

        results = await asyncio.gather(*(send_one(email) for email in pending), return_exceptions=True)
        sent_count = sum(1 for res in results if res is True)

    await db.commit()
    return sent_count
