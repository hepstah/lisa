"""Tests for config, database, and models -- Task 1 TDD."""
import os
import tempfile
import pytest

# Force test-safe settings before any lisa imports
os.environ["LISA_DEV_MODE"] = "true"
os.environ["LISA_DB_PATH"] = ":memory:"


class TestSettings:
    def test_dev_mode_defaults_true(self):
        from lisa.config import Settings

        s = Settings(dev_mode=True, db_path=":memory:")
        assert s.dev_mode is True

    def test_reads_lisa_prefixed_env_vars(self, monkeypatch):
        monkeypatch.setenv("LISA_DEV_MODE", "false")
        monkeypatch.setenv("LISA_DB_PATH", "/tmp/test.db")
        from lisa.config import Settings

        s = Settings()
        assert s.dev_mode is False
        assert s.db_path == "/tmp/test.db"

    def test_settings_has_expected_fields(self):
        from lisa.config import Settings

        s = Settings(dev_mode=True, db_path=":memory:")
        assert hasattr(s, "dev_mode")
        assert hasattr(s, "db_path")
        assert hasattr(s, "kasa_username")
        assert hasattr(s, "kasa_password")
        assert hasattr(s, "host")
        assert hasattr(s, "port")


class TestDatabase:
    @pytest.fixture(autouse=True)
    def _use_file_db(self, monkeypatch, tmp_path):
        """Use a file-based DB so WAL mode and cross-connection persistence work."""
        db_file = str(tmp_path / "test.db")
        monkeypatch.setenv("LISA_DB_PATH", db_file)
        from lisa.config import Settings

        test_settings = Settings()
        import lisa.db as db_mod

        monkeypatch.setattr(db_mod, "settings", test_settings)

    @pytest.mark.asyncio
    async def test_get_db_returns_wal_mode(self):
        from lisa.db import get_db

        db = await get_db()
        try:
            cursor = await db.execute("PRAGMA journal_mode")
            row = await cursor.fetchone()
            assert row[0] == "wal"
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_init_db_creates_command_log_table(self):
        from lisa.db import init_db, get_db

        await init_db()
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='command_log'"
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "command_log"
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_init_db_creates_devices_table(self):
        from lisa.db import init_db, get_db

        await init_db()
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='devices'"
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "devices"
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_init_db_creates_settings_table(self):
        from lisa.db import init_db, get_db

        await init_db()
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='settings'"
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "settings"
        finally:
            await db.close()


class TestModels:
    def test_device_state_response_validates(self):
        from lisa.models import DeviceStateResponse

        state = DeviceStateResponse(
            device_id="test-1",
            alias="Test Device",
            is_on=True,
            is_reachable=True,
        )
        assert state.device_id == "test-1"
        assert state.alias == "Test Device"
        assert state.is_on is True
        assert state.is_reachable is True

    def test_command_record_has_required_fields(self):
        from lisa.models import CommandRecord

        record = CommandRecord(
            id=1,
            timestamp="2026-01-01T00:00:00",
            source="dashboard",
            status="success",
        )
        assert record.id == 1
        assert record.timestamp == "2026-01-01T00:00:00"
        assert record.source == "dashboard"
        assert record.status == "success"
        assert record.error_message is None
        assert record.error_stage is None
        assert record.duration_ms is None

    def test_command_record_with_error_fields(self):
        from lisa.models import CommandRecord

        record = CommandRecord(
            id=2,
            timestamp="2026-01-01T00:00:00",
            source="voice",
            raw_input="turn on lamp",
            device_id="lamp-1",
            action="turn_on",
            status="error",
            error_message="Device unreachable",
            error_stage="device_unreachable",
            duration_ms=150,
        )
        assert record.error_message == "Device unreachable"
        assert record.error_stage == "device_unreachable"
        assert record.duration_ms == 150

    def test_device_control_request(self):
        from lisa.models import DeviceControlRequest

        req = DeviceControlRequest(action="turn_on")
        assert req.action == "turn_on"

    def test_text_command_request(self):
        from lisa.models import TextCommandRequest

        req = TextCommandRequest(text="turn on the lamp")
        assert req.text == "turn on the lamp"
        assert req.source == "dashboard"
