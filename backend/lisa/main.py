import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from lisa.config import settings
from lisa.db import init_db
from lisa.api import devices, commands
from lisa.api.ws import manager

logger = logging.getLogger("lisa")


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

    # Voice pipeline services (Phase 2)
    tts = None
    if settings.tts_model_path:
        from lisa.services.tts_service import TTSService

        try:
            tts = TTSService(
                model_path=settings.tts_model_path,
                output_dir=settings.tts_output_dir,
                dev_mode=settings.dev_mode,
            )
        except Exception as e:
            logger.warning("TTS unavailable: %s", e)

    llm = None
    if settings.anthropic_api_key:
        from lisa.services.llm_intent_service import LLMIntentService

        llm = LLMIntentService(
            api_key=settings.anthropic_api_key,
            model=settings.llm_model,
            timeout=settings.llm_timeout,
        )

    stt = None
    if settings.openai_api_key:
        from lisa.services.stt_service import STTService

        stt = STTService(
            api_key=settings.openai_api_key,
            model=settings.stt_model,
            timeout=settings.stt_timeout,
        )

    voice_pipeline = None
    if llm and tts:
        from lisa.services.voice_pipeline import VoicePipeline

        voice_pipeline = VoicePipeline(stt=stt, llm=llm, tts=tts, device_service=svc)
        logger.info("Voice pipeline active")
    else:
        if not llm:
            logger.info("Voice pipeline inactive: no LISA_ANTHROPIC_API_KEY")
        if not tts:
            logger.info("Voice pipeline inactive: no TTS model configured")

    # Inject into routers
    devices.device_service = svc
    commands.device_service = svc
    commands.voice_pipeline = voice_pipeline

    # Phase 3: Voice loop (Pi mode only)
    voice_loop = None
    if voice_pipeline and not settings.dev_mode:
        try:
            from lisa.voice.voice_loop import VoiceLoop
            from lisa.voice.wake_word import WakeWordDetector
            from lisa.voice.audio_capture import AudioCapture

            loop = asyncio.get_event_loop()

            async def pipeline_status_callback(status: str):
                await manager.broadcast({"type": "pipeline_status", "status": status})

            voice_loop = VoiceLoop(
                wake_detector=WakeWordDetector(),
                audio_capture=AudioCapture(),
                pipeline=voice_pipeline,
                event_loop=loop,
                status_callback=pipeline_status_callback,
            )
            voice_loop.start()
            logger.info("Voice loop started")
        except Exception as e:
            logger.warning("Voice loop unavailable: %s", e)
    else:
        if not voice_pipeline:
            logger.info("Voice loop skipped: voice pipeline not available")
        elif settings.dev_mode:
            logger.info("Voice loop skipped: dev mode (use /api/commands/text)")

    yield

    # Shutdown
    if voice_loop:
        voice_loop.stop()
        logger.info("Voice loop stopped")


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
