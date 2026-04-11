"""Tests for FakeAdapter and DeviceService -- Task 2 TDD."""
import os
import pytest

from lisa.device.fake_adapter import FakeAdapter


class TestFakeAdapter:
    @pytest.fixture
    def adapter(self):
        return FakeAdapter()

    @pytest.mark.asyncio
    async def test_discover_returns_3_devices(self, adapter):
        devices = await adapter.discover()
        assert len(devices) == 3

    @pytest.mark.asyncio
    async def test_discover_contains_expected_ids(self, adapter):
        devices = await adapter.discover()
        ids = {d.device_id for d in devices}
        assert ids == {"fake-lamp-1", "fake-plug-1", "fake-offline-1"}

    @pytest.mark.asyncio
    async def test_get_state_lamp_defaults(self, adapter):
        state = await adapter.get_state("fake-lamp-1")
        assert state.is_on is False
        assert state.is_reachable is True

    @pytest.mark.asyncio
    async def test_turn_on_changes_state(self, adapter):
        state = await adapter.turn_on("fake-lamp-1")
        assert state.is_on is True

    @pytest.mark.asyncio
    async def test_turn_off_changes_state(self, adapter):
        await adapter.turn_on("fake-lamp-1")
        state = await adapter.turn_off("fake-lamp-1")
        assert state.is_on is False

    @pytest.mark.asyncio
    async def test_turn_on_offline_raises_connection_error(self, adapter):
        with pytest.raises(ConnectionError):
            await adapter.turn_on("fake-offline-1")

    @pytest.mark.asyncio
    async def test_turn_off_offline_raises_connection_error(self, adapter):
        with pytest.raises(ConnectionError):
            await adapter.turn_off("fake-offline-1")

    @pytest.mark.asyncio
    async def test_get_state_unknown_raises_key_error(self, adapter):
        with pytest.raises(KeyError):
            await adapter.get_state("nonexistent")


class TestDeviceService:
    @pytest.fixture
    def _patch_db(self, monkeypatch, tmp_path):
        """Use file-based DB for command logging."""
        db_file = str(tmp_path / "test_service.db")
        monkeypatch.setenv("LISA_DB_PATH", db_file)
        from lisa.config import Settings

        test_settings = Settings()
        import lisa.db as db_mod

        monkeypatch.setattr(db_mod, "settings", test_settings)

    @pytest.fixture
    async def service(self, _patch_db):
        from lisa.db import init_db
        from lisa.services.device_service import DeviceService

        await init_db()
        adapter = FakeAdapter()
        svc = DeviceService(adapter)
        await svc.discover_devices()
        return svc

    @pytest.mark.asyncio
    async def test_execute_validates_before_adapter(self, service):
        """Invalid action should be rejected without calling adapter."""
        svc = service
        state, log = await svc.execute_command("fake-lamp-1", "reboot")
        assert state is None
        assert log["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_execute_logs_to_command_log(self, service):
        """Successful command should be logged."""
        svc = service
        state, log = await svc.execute_command("fake-lamp-1", "turn_on")
        assert log["status"] == "success"
        assert log["id"] is not None

    @pytest.mark.asyncio
    async def test_execute_rejected_unknown_device(self, service):
        svc = service
        state, log = await svc.execute_command("unknown-device", "turn_on")
        assert state is None
        assert log["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_execute_success_returns_new_state(self, service):
        svc = service
        state, log = await svc.execute_command("fake-lamp-1", "turn_on")
        assert state is not None
        assert state.is_on is True

    @pytest.mark.asyncio
    async def test_execute_unreachable_logs_error(self, service):
        svc = service
        state, log = await svc.execute_command("fake-offline-1", "turn_on")
        assert state is None
        assert log["status"] == "error"
        assert log["error_stage"] == "device_unreachable"

    @pytest.mark.asyncio
    async def test_get_state_calls_adapter_live(self, service):
        """get_device_state queries live state per DEVICE-03."""
        svc = service
        state = await svc.get_device_state("fake-lamp-1")
        assert state.device_id == "fake-lamp-1"
        assert state.is_reachable is True
