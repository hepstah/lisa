from pydantic import BaseModel
from typing import Optional


class DeviceStateResponse(BaseModel):
    device_id: str
    alias: str
    is_on: bool
    is_reachable: bool


class DeviceControlRequest(BaseModel):
    action: str  # "turn_on" or "turn_off"


class TextCommandRequest(BaseModel):
    text: str
    source: str = "dashboard"


class CommandRecord(BaseModel):
    id: int
    timestamp: str
    source: str
    raw_input: Optional[str] = None
    device_id: Optional[str] = None
    action: Optional[str] = None
    status: str  # "success", "error", "rejected"
    error_message: Optional[str] = None
    error_stage: Optional[str] = None
    duration_ms: Optional[int] = None
    llm_debug: Optional[dict] = None


class DeviceConfigRequest(BaseModel):
    host: str
    alias: str
    device_type: str = "plug"
    kasa_username: Optional[str] = None
    kasa_password: Optional[str] = None
