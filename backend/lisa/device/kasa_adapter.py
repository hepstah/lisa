from kasa import Discover, Credentials
from lisa.device.interface import DeviceState
from lisa.config import Settings


class KasaAdapter:
    """Real TP-Link Kasa adapter using python-kasa. Per D-01, D-02."""

    def __init__(self, settings: Settings):
        self._credentials = Credentials(
            settings.kasa_username,
            settings.kasa_password,
        ) if settings.kasa_username else None
        self._devices: dict[str, object] = {}  # device_id -> kasa Device

    async def discover(self) -> list[DeviceState]:
        found = await Discover.discover(credentials=self._credentials)
        states = []
        for ip, dev in found.items():
            await dev.update()
            self._devices[ip] = dev
            states.append(DeviceState(
                device_id=ip,
                alias=dev.alias,
                is_on=dev.is_on,
                is_reachable=True,
            ))
        return states

    async def get_state(self, device_id: str) -> DeviceState:
        dev = self._devices.get(device_id)
        if not dev:
            dev = await Discover.discover_single(
                device_id, credentials=self._credentials
            )
            self._devices[device_id] = dev
        try:
            await dev.update()  # Always live query per DEVICE-03
            return DeviceState(
                device_id=device_id,
                alias=dev.alias,
                is_on=dev.is_on,
                is_reachable=True,
            )
        except Exception:
            return DeviceState(
                device_id=device_id,
                alias=getattr(dev, "alias", device_id),
                is_on=False,
                is_reachable=False,
            )

    async def turn_on(self, device_id: str) -> DeviceState:
        dev = self._devices[device_id]
        await dev.turn_on()
        await dev.update()  # Per Pitfall 4: always update after state change
        return DeviceState(
            device_id=device_id,
            alias=dev.alias,
            is_on=dev.is_on,
            is_reachable=True,
        )

    async def turn_off(self, device_id: str) -> DeviceState:
        dev = self._devices[device_id]
        await dev.turn_off()
        await dev.update()  # Per Pitfall 4: always update after state change
        return DeviceState(
            device_id=device_id,
            alias=dev.alias,
            is_on=dev.is_on,
            is_reachable=True,
        )
