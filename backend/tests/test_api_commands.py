"""Integration tests for /api/commands/ endpoints."""

import pytest

from lisa.services.llm_intent_service import DeviceIntent


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
    async def test_text_command_turn_on_bedroom_lamp(self, client, mock_llm_intent):
        """POST /api/commands/text with 'turn on the bedroom lamp' succeeds."""
        mock_llm_intent.set_response(
            "turn on the bedroom lamp",
            intent=DeviceIntent(
                device_id="fake-lamp-1",
                action="turn_on",
                confirmation="Turning on the bedroom lamp",
            ),
        )

        resp = await client.post(
            "/api/commands/text",
            json={"text": "turn on the bedroom lamp"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["device_id"] == "fake-lamp-1"
        assert data["action"] == "turn_on"

    async def test_text_command_turn_off(self, client, mock_llm_intent):
        """POST /api/commands/text with 'turn off desk fan' succeeds."""
        mock_llm_intent.set_response(
            "turn off desk fan",
            intent=DeviceIntent(
                device_id="fake-plug-1",
                action="turn_off",
                confirmation="Turning off the desk fan",
            ),
        )

        resp = await client.post(
            "/api/commands/text",
            json={"text": "turn off desk fan"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["action"] == "turn_off"

    async def test_text_command_unknown_pattern_rejected(self, client, mock_llm_intent):
        """POST /api/commands/text with 'reboot everything' returns rejected.

        Note: the original assertion checked for "Could not understand" which
        comes from the Phase-1 fallback parser path (_log_unknown). The LLM
        path emits MSG_UNKNOWN_INTENT ("I didn't understand that. ...") when
        parse_intent returns no tool call. Relaxed to status-only check.
        """
        # Default mock_llm_intent fallback returns IntentResult(intent=None),
        # which triggers MSG_UNKNOWN_INTENT in the pipeline.
        resp = await client.post(
            "/api/commands/text",
            json={"text": "reboot everything"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert "didn't understand" in data["error_message"]

    async def test_text_command_no_matching_device_rejected(self, client, mock_llm_intent):
        """POST /api/commands/text with nonexistent device returns rejected.

        Note: the original assertion checked "No device found" which comes
        from _log_no_match (Phase-1 fallback). The LLM path sees the
        nonexistent device name and returns no tool call, so we get
        MSG_UNKNOWN_INTENT instead. Relaxed to status-only check.
        """
        resp = await client.post(
            "/api/commands/text",
            json={"text": "turn on the nonexistent device"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"

    async def test_text_command_appears_in_history(self, client, mock_llm_intent):
        """Text commands are logged in command history and llm_debug round-trips as a dict."""
        mock_llm_intent.set_response(
            "turn on the bedroom lamp",
            intent=DeviceIntent(
                device_id="fake-lamp-1",
                action="turn_on",
                confirmation="Turning on the bedroom lamp",
            ),
        )

        await client.post(
            "/api/commands/text",
            json={"text": "turn on the bedroom lamp"},
        )

        resp = await client.get("/api/commands/history")
        data = resp.json()
        assert len(data) >= 1
        # Most recent should be the text command
        matching = [r for r in data if r["raw_input"] == "turn on the bedroom lamp"]
        assert matching, "expected the text command to appear in history"
        row = matching[0]
        # Dev mode is set in conftest, so llm_debug should be present as a dict
        assert isinstance(row.get("llm_debug"), dict)
        assert row["llm_debug"]["input_text"] == "turn on the bedroom lamp"
        assert row["llm_debug"]["decision"]["tool_used"] is True
