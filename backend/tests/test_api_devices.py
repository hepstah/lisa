"""Integration tests for /api/devices/ endpoints."""

import pytest


class TestListDevices:
    async def test_list_devices(self, client):
        """GET /api/devices/ returns list of 3 fake devices."""
        resp = await client.get("/api/devices/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    async def test_list_devices_has_expected_fields(self, client):
        """Each device has device_id, alias, is_on, is_reachable."""
        resp = await client.get("/api/devices/")
        data = resp.json()
        for device in data:
            assert "device_id" in device
            assert "alias" in device
            assert "is_on" in device
            assert "is_reachable" in device

    async def test_list_devices_contains_fake_lamp(self, client):
        """Device list contains fake-lamp-1."""
        resp = await client.get("/api/devices/")
        ids = [d["device_id"] for d in resp.json()]
        assert "fake-lamp-1" in ids


class TestGetDevice:
    async def test_get_device_lamp(self, client):
        """GET /api/devices/fake-lamp-1 returns device with is_on=False."""
        resp = await client.get("/api/devices/fake-lamp-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["device_id"] == "fake-lamp-1"
        assert data["alias"] == "Bedroom Lamp"
        assert data["is_on"] is False
        assert data["is_reachable"] is True

    async def test_get_device_not_found(self, client):
        """GET /api/devices/nonexistent returns 404."""
        resp = await client.get("/api/devices/nonexistent")
        assert resp.status_code == 404


class TestControlDevice:
    async def test_control_device_turn_on(self, client):
        """POST /api/devices/fake-lamp-1/control with turn_on returns success."""
        resp = await client.post(
            "/api/devices/fake-lamp-1/control",
            json={"action": "turn_on"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["device_id"] == "fake-lamp-1"
        assert data["action"] == "turn_on"

    async def test_control_device_turn_on_updates_state(self, client):
        """After turn_on, device state shows is_on=True."""
        await client.post(
            "/api/devices/fake-lamp-1/control",
            json={"action": "turn_on"},
        )
        resp = await client.get("/api/devices/fake-lamp-1")
        assert resp.json()["is_on"] is True

    async def test_control_device_invalid_action_rejected(self, client):
        """POST /api/devices/fake-lamp-1/control with reboot returns rejected."""
        resp = await client.post(
            "/api/devices/fake-lamp-1/control",
            json={"action": "reboot"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert "not allowed" in data["error_message"].lower()

    async def test_control_offline_device_returns_error(self, client):
        """POST /api/devices/fake-offline-1/control with turn_on returns error."""
        resp = await client.post(
            "/api/devices/fake-offline-1/control",
            json={"action": "turn_on"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"
        assert data["error_stage"] == "device_unreachable"


class TestDiscoverDevices:
    async def test_discover_devices(self, client):
        """POST /api/devices/discover returns 3 devices."""
        resp = await client.post("/api/devices/discover")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
