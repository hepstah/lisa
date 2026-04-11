from fastapi import APIRouter, HTTPException
from lisa.models import DeviceStateResponse, DeviceControlRequest, DeviceConfigRequest
from lisa.api.ws import manager

router = APIRouter(prefix="/api/devices", tags=["devices"])

# The device_service instance will be set in main.py at startup
device_service = None


@router.get("/", response_model=list[DeviceStateResponse])
async def list_devices():
    """List all known devices with live state."""
    states = await device_service.get_all_states()
    return [
        DeviceStateResponse(
            device_id=s.device_id,
            alias=s.alias,
            is_on=s.is_on,
            is_reachable=s.is_reachable,
        )
        for s in states
    ]


@router.get("/{device_id}", response_model=DeviceStateResponse)
async def get_device(device_id: str):
    """Get live state of a single device. Per DEVICE-03."""
    try:
        state = await device_service.get_device_state(device_id)
        return DeviceStateResponse(
            device_id=state.device_id,
            alias=state.alias,
            is_on=state.is_on,
            is_reachable=state.is_reachable,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")


@router.post("/{device_id}/control", response_model=dict)
async def control_device(device_id: str, req: DeviceControlRequest):
    """Control a device (turn_on/turn_off). Per DEVICE-04."""
    new_state, log = await device_service.execute_command(
        device_id=device_id,
        action=req.action,
        source="api",
    )
    if new_state:
        await manager.broadcast(
            {
                "type": "device_state",
                "device_id": new_state.device_id,
                "alias": new_state.alias,
                "is_on": new_state.is_on,
                "is_reachable": new_state.is_reachable,
            }
        )
        await manager.broadcast({"type": "command_logged", "command": log})
    else:
        await manager.broadcast({"type": "command_logged", "command": log})
    return log


@router.post("/discover", response_model=list[DeviceStateResponse])
async def discover_devices():
    """Discover devices on the network."""
    states = await device_service.discover_devices()
    return [
        DeviceStateResponse(
            device_id=s.device_id,
            alias=s.alias,
            is_on=s.is_on,
            is_reachable=s.is_reachable,
        )
        for s in states
    ]


@router.post("/add", response_model=dict)
async def add_device(req: DeviceConfigRequest):
    """Manually add a device. Per DASH-03."""
    device_service.register_device(req.host)
    from lisa.db import get_db

    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO devices (device_id, alias, device_type, host) VALUES (?, ?, ?, ?)",
            (req.host, req.alias, req.device_type, req.host),
        )
        await db.commit()
    finally:
        await db.close()
    return {"status": "added", "device_id": req.host, "alias": req.alias}
