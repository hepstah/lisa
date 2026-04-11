"""Continuous wake word -> capture -> pipeline loop in a background thread.

Pi-only module. In dev mode this is never instantiated; text injection
via /api/commands/text bypasses audio entirely.
"""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)

# Graceful import: pyaudio requires portaudio and may not be available
# on all platforms (dev machines, CI).
try:
    import pyaudio

    PYAUDIO_AVAILABLE = True
except ImportError:
    pyaudio = None  # type: ignore[assignment]
    PYAUDIO_AVAILABLE = False


class VoiceLoop:
    """Drives wake word detection, audio capture, and pipeline execution.

    Runs a blocking audio loop in a daemon thread. Bridges back to the
    main asyncio event loop via run_coroutine_threadsafe for pipeline
    calls and status broadcasts.
    """

    SAMPLE_RATE = 16000
    CHANNELS = 1
    FRAME_SIZE = 1280  # 80ms at 16kHz, 16-bit mono
    PIPELINE_TIMEOUT = 15  # seconds
    COOLDOWN = 0.5  # seconds after TTS before re-enabling wake detection

    def __init__(self, wake_detector, audio_capture, pipeline, event_loop, status_callback):
        self._wake = wake_detector
        self._capture = audio_capture
        self._pipeline = pipeline
        self._loop = event_loop
        self._status_cb = status_callback
        self._running = False
        self._thread = None

    def start(self):
        """Start the audio loop in a daemon thread."""
        import threading

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="voice-loop")
        self._thread.start()

    def stop(self):
        """Signal the loop to stop and wait for the thread to finish."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _emit_status(self, status: str):
        """Broadcast a pipeline status event via the async callback."""
        asyncio.run_coroutine_threadsafe(self._status_cb(status), self._loop)

    def _run(self):
        """Main blocking audio loop. Runs in a background thread."""
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError(
                "pyaudio not available -- voice loop requires Pi environment"
            )

        pa = None
        stream = None
        try:
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                input=True,
                frames_per_buffer=self.FRAME_SIZE,
            )

            self._emit_status("listening")
            logger.info("Voice loop started, listening for wake word")

            while self._running:
                frame = stream.read(self.FRAME_SIZE, exception_on_overflow=False)

                detections = self._wake.detect(frame)
                if not detections:
                    continue

                # Wake word detected
                names = ", ".join(detections.keys())
                logger.info("Wake word detected: %s", names)
                self._emit_status("processing")

                # Capture speech
                self._capture.reset()
                self._capture.process_frame(frame)

                while self._running:
                    cap_frame = stream.read(self.FRAME_SIZE, exception_on_overflow=False)
                    if not self._capture.process_frame(cap_frame):
                        break

                audio_bytes = self._capture.get_audio()

                # Mute wake detector during pipeline + TTS
                self._wake.mute()

                try:
                    future = asyncio.run_coroutine_threadsafe(
                        self._pipeline.process_audio(audio_bytes), self._loop
                    )
                    future.result(timeout=self.PIPELINE_TIMEOUT)
                except Exception:
                    logger.exception("Pipeline error")
                    self._emit_status("error")

                self._emit_status("responding")

                # Cooldown before re-enabling wake detection (echo prevention)
                time.sleep(self.COOLDOWN)

                self._wake.unmute()
                self._emit_status("listening")

        except Exception:
            logger.exception("Voice loop crashed")
            self._emit_status("error")
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if pa is not None:
                try:
                    pa.terminate()
                except Exception:
                    pass
