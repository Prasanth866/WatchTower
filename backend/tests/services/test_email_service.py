import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from models.email_queue import EmailQueue
from services.email_service import send_pending_emails
from core.config import get_settings

settings = get_settings()


@pytest.mark.asyncio
async def test_send_pending_emails_returns_zero_if_not_configured() -> None:
    with patch.object(settings, "BREVO_API_KEY", ""), \
         patch.object(settings, "BREVO_FROM_EMAIL", ""):
        
        db = AsyncMock(spec=AsyncSession)
        sent = await send_pending_emails(db)
        assert sent == 0


@pytest.mark.asyncio
async def test_send_pending_emails_dispatches_http_requests() -> None:
    with patch.object(settings, "BREVO_API_KEY", "xkeysib-testkey123"), \
         patch.object(settings, "BREVO_FROM_EMAIL", "sender@test.dev"), \
         patch.object(settings, "BREVO_SENDER_NAME", "WatchTower"):
        
        user_id = uuid4()
        email_record = EmailQueue(
            user_id=user_id,
            to_email="receiver@test.dev",
            subject="Alert Test",
            body="Coin threshold breached",
            sent=False,
        )

        db = AsyncMock(spec=AsyncSession)
        from unittest.mock import MagicMock
        db_result = MagicMock()
        db_result.scalars.return_value.all.return_value = [email_record]
        db.execute.return_value = db_result

        # Mock httpx.AsyncClient.post
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
            sent_count = await send_pending_emails(db)
            
            assert sent_count == 1
            assert email_record.sent is True
            assert email_record.sent_at is not None
            
            # Assert httpx mock call parameters
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "https://api.brevo.com/v3/smtp/email"
            assert kwargs["headers"]["api-key"] == "xkeysib-testkey123"
            assert kwargs["headers"]["accept"] == "application/json"
            assert kwargs["json"]["sender"] == {"name": "WatchTower", "email": "sender@test.dev"}
            assert kwargs["json"]["to"] == [{"email": "receiver@test.dev"}]
            assert kwargs["json"]["subject"] == "Alert Test"
            assert kwargs["json"]["textContent"] == "Coin threshold breached"
            
            db.commit.assert_called_once()
