import time
from typing import Optional
from lisa.device.interface import DeviceAdapter, DeviceState
from lisa.services.allowlist import validate_action
from lisa.db import get_db


class DeviceService:
    """Business logic layer: validate, execute, log. Per DEVICE-02, DEVICE-03."""

    def __init__(self, adapter: DeviceAdapter):
        self._adapter = adapter
        self._known_device_ids: set[str] = set()

    async def discover_devices(self) -> list[DeviceState]:
        states = await self._adapter.discover()
        self._known_device_ids = {s.device_id for s in states}
        return states

    async def get_device_state(self, device_id: str) -> DeviceState:
        """Query live state per DEVICE-03 -- never cached."""
        return await self._adapter.get_state(device_id)

    async def get_all_states(self) -> list[DeviceState]:
        states = []
        for did in self._known_device_ids:
            states.append(await self._adapter.get_state(did))
        return states

    def register_device(self, device_id: str):
        """Add a device ID to the known set."""
        self._known_device_ids.add(device_id)

    async def execute_command(
        self,
        device_id: str,
        action: str,
        source: str = "dashboard",
        raw_input: Optional[str] = None,
        llm_debug: Optional[str] = None,
    ) -> tuple[DeviceState | None, dict]:
        """Execute a device command with validation and logging.

        Returns (new_state_or_None, log_record_dict).
        Per DEVICE-02: validates against allowlist before execution.
        Per ERR-02: logs all results including failures.

        llm_debug is an opaque JSON string (or None) that the voice pipeline
        attaches in dev mode. DeviceService never inspects it -- it is written
        through to the command_log row and returned in the log dict.
        """
        start = time.monotonic()

        # Validate per DEVICE-02
        is_valid, rejection_reason = validate_action(
            action, device_id, self._known_device_ids
        )

        if not is_valid:
            log = await self._log_command(
                source=source,
                raw_input=raw_input,
                device_id=device_id,
                action=action,
                status="rejected",
                error_message=rejection_reason,
                error_stage="validation",
                duration_ms=int((time.monotonic() - start) * 1000),
                llm_debug=llm_debug,
            )
            return None, log

        # Execute
        try:
            if action == "turn_on":
                new_state = await self._adapter.turn_on(device_id)
            elif action == "turn_off":
                new_state = await self._adapter.turn_off(device_id)
            else:
                raise ValueError(f"Unknown action: {action}")

            duration = int((time.monotonic() - start) * 1000)
            log = await self._log_command(
                source=source,
                raw_input=raw_input,
                device_id=device_id,
                action=action,
                status="success",
                duration_ms=duration,
                llm_debug=llm_debug,
            )
            return new_state, log

        except ConnectionError as e:
            duration = int((time.monotonic() - start) * 1000)
            log = await self._log_command(
                source=source,
                raw_input=raw_input,
                device_id=device_id,
                action=action,
                status="error",
                error_message=str(e),
                error_stage="device_unreachable",
                duration_ms=duration,
                llm_debug=llm_debug,
            )
            return None, log

        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            log = await self._log_command(
                source=source,
                raw_input=raw_input,
                device_id=device_id,
                action=action,
                status="error",
                error_message=str(e),
                error_stage="execution",
                duration_ms=duration,
                llm_debug=llm_debug,
            )
            return None, log

    async def _log_command(self, **kwargs) -> dict:
        """Log command to SQLite per ERR-02."""
        db = await get_db()
        try:
            cursor = await db.execute(
                """INSERT INTO command_log
                   (source, raw_input, device_id, action, status,
                    error_message, error_stage, duration_ms, llm_debug)
                   VALUES (:source, :raw_input, :device_id, :action,
                           :status, :error_message, :error_stage,
                           :duration_ms, :llm_debug)""",
                {
                    "source": kwargs.get("source", "unknown"),
                    "raw_input": kwargs.get("raw_input"),
                    "device_id": kwargs.get("device_id"),
                    "action": kwargs.get("action"),
                    "status": kwargs.get("status", "error"),
                    "error_message": kwargs.get("error_message"),
                    "error_stage": kwargs.get("error_stage"),
                    "duration_ms": kwargs.get("duration_ms"),
                    "llm_debug": kwargs.get("llm_debug"),
                },
            )
            await db.commit()
            return {**kwargs, "id": cursor.lastrowid}
        finally:
            await db.close()
