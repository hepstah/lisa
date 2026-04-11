from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from lisa.config import settings
from lisa.db import init_db
from lisa.api import devices, commands
from lisa.api.ws import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()

    if settings.dev_mode:
        from lisa.device.fake_adapter import FakeAdapter

        adapter = FakeAdapter()
    else:
        from lisa.device.kasa_adapter import KasaAdapter

        adapter = KasaAdapter(settings)

    from lisa.services.device_service import DeviceService

    svc = DeviceService(adapter)

    # Discover devices on startup
    await svc.discover_devices()

    # Inject into routers
    devices.device_service = svc
    commands.device_service = svc

    yield

    # Shutdown (nothing to clean up)


app = FastAPI(title="Lisa Smart Home", lifespan=lifespan)

# API routers
app.include_router(devices.router)
app.include_router(commands.router)


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            # Future: handle incoming WS messages (e.g., text commands via WS)
    except WebSocketDisconnect:
        manager.disconnect(ws)


# SPA static files (production only)
dashboard_dir = Path(__file__).parent.parent.parent / "dashboard" / "dist"
if dashboard_dir.exists():
    app.mount(
        "/", StaticFiles(directory=str(dashboard_dir), html=True), name="dashboard"
    )
