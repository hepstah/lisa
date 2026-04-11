from lisa.device.interface import DeviceState


class FakeAdapter:
    """In-memory fake for development without hardware. Per D-03, D-04."""

    def __init__(self):
        self._devices: dict[str, DeviceState] = {
            "fake-lamp-1": DeviceState(
                device_id="fake-lamp-1",
                alias="Bedroom Lamp",
                is_on=False,
                is_reachable=True,
            ),
            "fake-plug-1": DeviceState(
                device_id="fake-plug-1",
                alias="Desk Fan",
                is_on=True,
                is_reachable=True,
            ),
            "fake-offline-1": DeviceState(
                device_id="fake-offline-1",
                alias="Garage Light",
                is_on=False,
                is_reachable=False,
            ),
        }

    async def discover(self) -> list[DeviceState]:
        return list(self._devices.values())

    async def get_state(self, device_id: str) -> DeviceState:
        if device_id not in self._devices:
            raise KeyError(f"Unknown device: {device_id}")
        return self._devices[device_id]

    async def turn_on(self, device_id: str) -> DeviceState:
        dev = self._devices[device_id]
        if not dev.is_reachable:
            raise ConnectionError(f"Device {device_id} is not reachable")
        self._devices[device_id] = DeviceState(
            device_id=dev.device_id,
            alias=dev.alias,
            is_on=True,
            is_reachable=True,
        )
        return self._devices[device_id]

    async def turn_off(self, device_id: str) -> DeviceState:
        dev = self._devices[device_id]
        if not dev.is_reachable:
            raise ConnectionError(f"Device {device_id} is not reachable")
        self._devices[device_id] = DeviceState(
            device_id=dev.device_id,
            alias=dev.alias,
            is_on=False,
            is_reachable=True,
        )
        return self._devices[device_id]

    def add_device(
        self,
        device_id: str,
        alias: str,
        is_on: bool = False,
        is_reachable: bool = True,
    ):
        """Add a device dynamically (for DeviceConfig flow)."""
        self._devices[device_id] = DeviceState(
            device_id=device_id,
            alias=alias,
            is_on=is_on,
            is_reachable=is_reachable,
        )
