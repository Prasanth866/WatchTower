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
    # Temporarily clear configuration
    with patch.object(settings, "RESEND_API_KEY", ""), \
         patch.object(settings, "RESEND_FROM_EMAIL", ""):
        
        db = AsyncMock(spec=AsyncSession)
        sent = await send_pending_emails(db)
        assert sent == 0


@pytest.mark.asyncio
async def test_send_pending_emails_dispatches_http_requests() -> None:
    # Mock settings
    with patch.object(settings, "RESEND_API_KEY", "re_testkey123"), \
         patch.object(settings, "RESEND_FROM_EMAIL", "sender@test.dev"):
        
        user_id = uuid4()
        email_record = EmailQueue(
            user_id=user_id,
            to_email="receiver@test.dev",
            subject="Alert Test",
            body="Coin threshold breached",
            sent=False,
        )

        db = AsyncMock(spec=AsyncSession)
        # Mock database results
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
            assert args[0] == "https://api.resend.com/emails"
            assert kwargs["headers"]["Authorization"] == "Bearer re_testkey123"
            assert kwargs["json"]["from"] == "sender@test.dev"
            assert kwargs["json"]["to"] == ["receiver@test.dev"]
            assert kwargs["json"]["subject"] == "Alert Test"
            assert kwargs["json"]["text"] == "Coin threshold breached"
            
            db.commit.assert_called_once()
