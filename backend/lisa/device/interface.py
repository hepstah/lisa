from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class DeviceState:
    """Immutable snapshot of device state."""
    device_id: str
    alias: str
    is_on: bool
    is_reachable: bool


@runtime_checkable
class DeviceAdapter(Protocol):
    """Minimal interface for device control. One integration, not a framework."""

    async def discover(self) -> list[DeviceState]:
        """Find devices on the network."""
        ...

    async def get_state(self, device_id: str) -> DeviceState:
        """Query live device state. Never cached. (DEVICE-03)"""
        ...

    async def turn_on(self, device_id: str) -> DeviceState:
        """Turn device on. Returns new state after update()."""
        ...

    async def turn_off(self, device_id: str) -> DeviceState:
        """Turn device off. Returns new state after update()."""
        ...
