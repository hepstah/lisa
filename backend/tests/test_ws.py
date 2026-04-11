"""Integration tests for WebSocket endpoint and ConnectionManager."""

import pytest
from starlette.testclient import TestClient
from lisa.main import app
from lisa.api.ws import ConnectionManager


class TestWebSocket:
    def test_websocket_connect(self):
        """WebSocket at /ws accepts connections."""
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws:
                # If we get here, connection was accepted
                assert ws is not None


class TestConnectionManager:
    """Unit tests for ConnectionManager (no HTTP needed)."""

    async def test_broadcast_to_no_clients(self):
        """Broadcast to empty list does not raise."""
        mgr = ConnectionManager()
        await mgr.broadcast({"type": "test"})

    async def test_disconnect_removes_client(self):
        """Disconnect removes a client from the active list."""
        mgr = ConnectionManager()

        class FakeWS:
            pass

        ws = FakeWS()
        mgr.active.append(ws)
        assert len(mgr.active) == 1
        mgr.disconnect(ws)
        assert len(mgr.active) == 0

    async def test_disconnect_nonexistent_is_noop(self):
        """Disconnecting a non-connected client does not raise."""
        mgr = ConnectionManager()

        class FakeWS:
            pass

        ws = FakeWS()
        mgr.disconnect(ws)
        assert len(mgr.active) == 0
