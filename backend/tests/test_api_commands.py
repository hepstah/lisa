"""Integration tests for /api/commands/ endpoints."""

import pytest


class TestCommandHistory:
    async def test_command_history_initially_empty(self, client):
        """GET /api/commands/history returns empty list initially."""
        resp = await client.get("/api/commands/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data == []

    async def test_command_history_after_command(self, client):
        """After a successful command, history returns 1 record."""
        # Execute a command first
        await client.post(
            "/api/devices/fake-lamp-1/control",
            json={"action": "turn_on"},
        )

        resp = await client.get("/api/commands/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["status"] == "success"
        assert data[0]["device_id"] == "fake-lamp-1"
        assert data[0]["action"] == "turn_on"


class TestTextCommand:
    async def test_text_command_turn_on_bedroom_lamp(self, client):
        """POST /api/commands/text with 'turn on the bedroom lamp' succeeds."""
        resp = await client.post(
            "/api/commands/text",
            json={"text": "turn on the bedroom lamp"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["device_id"] == "fake-lamp-1"
        assert data["action"] == "turn_on"

    async def test_text_command_turn_off(self, client):
        """POST /api/commands/text with 'turn off desk fan' succeeds."""
        resp = await client.post(
            "/api/commands/text",
            json={"text": "turn off desk fan"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["action"] == "turn_off"

    async def test_text_command_unknown_pattern_rejected(self, client):
        """POST /api/commands/text with 'reboot everything' returns rejected."""
        resp = await client.post(
            "/api/commands/text",
            json={"text": "reboot everything"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert "Could not understand" in data["error_message"]

    async def test_text_command_no_matching_device_rejected(self, client):
        """POST /api/commands/text with nonexistent device returns rejected."""
        resp = await client.post(
            "/api/commands/text",
            json={"text": "turn on the nonexistent device"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert "No device found" in data["error_message"]

    async def test_text_command_appears_in_history(self, client):
        """Text commands are logged in command history."""
        await client.post(
            "/api/commands/text",
            json={"text": "turn on the bedroom lamp"},
        )

        resp = await client.get("/api/commands/history")
        data = resp.json()
        assert len(data) >= 1
        # Most recent should be the text command
        found = any(
            r["raw_input"] == "turn on the bedroom lamp" for r in data
        )
        assert found
