import pytest
import asyncio
from fastapi.testclient import TestClient
from main import app
from core.security import create_access_token
from schemas.event import Event

def test_websocket_rejects_unauthenticated():
    client = TestClient(app)
    # Connecting without a token should fail and close the connection
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/ws/btc") as ws:
            pass

def test_websocket_accepts_authenticated_and_receives_broadcast():
    token = create_access_token(data={"sub": "00000000-0000-0000-0000-000000000001"})
    
    with TestClient(app) as client:
        with client.websocket_connect(f"/api/v1/ws/btc?token={token}") as ws:
            manager = app.state.manager
            
            event = Event(
                topic="btc",
                value=63500.2,
                unit="USD",
                metadata={"coin": "bitcoin", "source": "test"}
            )
            
            # Broadcast the event
            asyncio.run(manager._broadcast("btc", event))
            
            # Receive and assert the broadcasted event
            data = ws.receive_json()
            assert data["topic"] == "btc"
            assert data["value"] == 63500.2
            assert data["unit"] == "USD"
