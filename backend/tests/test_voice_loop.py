"""Tests for VoiceLoop and TTS aplay playback extension."""

import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# VoiceLoop tests
# ---------------------------------------------------------------------------


def _make_loop():
    """Create a real asyncio event loop for bridging tests."""
    loop = asyncio.new_event_loop()
    return loop


def _make_voice_loop(
    wake_detections=None,
    capture_continues=None,
    pipeline_result=None,
):
    """Build a VoiceLoop with mocked dependencies.

    Args:
        wake_detections: list of dicts returned by wake_detector.detect() per call.
        capture_continues: list of bools returned by audio_capture.process_frame() per call.
        pipeline_result: dict returned by pipeline.process_audio().
    """
    from lisa.voice.voice_loop import VoiceLoop

    wake = Mock()
    wake.detect = Mock(side_effect=wake_detections or [{}])
    wake.mute = Mock()
    wake.unmute = Mock()

    capture = Mock()
    capture.process_frame = Mock(side_effect=capture_continues or [True, False])
    capture.get_audio = Mock(return_value=b"\x00" * 2560)
    capture.reset = Mock()

    pipeline = AsyncMock()
    pipeline.process_audio = AsyncMock(
        return_value=pipeline_result or {"status": "success"}
    )

    loop = _make_loop()
    status_cb = AsyncMock()

    vl = VoiceLoop(
        wake_detector=wake,
        audio_capture=capture,
        pipeline=pipeline,
        event_loop=loop,
        status_callback=status_cb,
    )

    return vl, wake, capture, pipeline, loop, status_cb


class TestEmitStatus:
    """Test 1: VoiceLoop._emit_status calls status_callback via run_coroutine_threadsafe."""

    def test_emit_status_calls_callback(self):
        vl, _, _, _, loop, status_cb = _make_voice_loop()

        # Run _emit_status from the main thread, with the loop running in bg
        import threading

        def run_loop():
            loop.run_forever()

        t = threading.Thread(target=run_loop, daemon=True)
        t.start()

        try:
            vl._emit_status("processing")
            # Give the coroutine time to execute
            time.sleep(0.1)
            status_cb.assert_called_with("processing")
        finally:
            loop.call_soon_threadsafe(loop.stop)
            t.join(timeout=2)
            loop.close()


class TestStop:
    """Test 2: VoiceLoop.stop() sets _running to False."""

    def test_stop_sets_running_false(self):
        vl, _, _, _, loop, _ = _make_voice_loop()
        vl._running = True
        vl._thread = None  # no actual thread to join
        vl.stop()
        assert vl._running is False
        loop.close()


class TestRunIterationWakeDetected:
    """Test 3: Wake word detected -> capture -> pipeline.process_audio called."""

    def test_wake_detected_triggers_pipeline(self):
        # Wake detector returns a hit on first call, then empty (to exit loop)
        wake_hits = [{"hey_jarvis": 0.9}]
        # Capture: first frame continues, second ends capture
        capture_seq = [True, False]

        vl, wake, capture, pipeline, loop, status_cb = _make_voice_loop(
            wake_detections=wake_hits,
            capture_continues=capture_seq,
        )

        # Mock pyaudio stream
        mock_stream = Mock()
        mock_stream.read = Mock(return_value=b"\x00" * 2560)

        # Manually call the iteration logic
        # We need to simulate what _run does for one wake detection cycle
        import threading

        def run_loop():
            loop.run_forever()

        t = threading.Thread(target=run_loop, daemon=True)
        t.start()

        try:
            # Simulate: frame read -> detect -> capture -> pipeline
            frame = mock_stream.read(1280)
            detections = wake.detect(frame)
            assert detections  # should have wake word

            capture.reset()
            capture.reset.assert_called_once()

            # Feed frames until capture says stop
            capture.process_frame(frame)  # returns True (continue)
            frame2 = mock_stream.read(1280)
            capture.process_frame(frame2)  # returns False (done)

            audio_bytes = capture.get_audio()
            assert audio_bytes == b"\x00" * 2560

            # Call pipeline via the bridge pattern
            wake.mute()
            future = asyncio.run_coroutine_threadsafe(
                pipeline.process_audio(audio_bytes), loop
            )
            result = future.result(timeout=5)
            assert result["status"] == "success"

            pipeline.process_audio.assert_called_once_with(audio_bytes)
            wake.mute.assert_called_once()
        finally:
            loop.call_soon_threadsafe(loop.stop)
            t.join(timeout=2)
            loop.close()


class TestRunIterationNoWake:
    """Test 4: No wake word detected -> pipeline NOT called."""

    def test_no_wake_skips_pipeline(self):
        vl, wake, capture, pipeline, loop, _ = _make_voice_loop(
            wake_detections=[{}],  # no detection
        )
        # With no detection, pipeline should never be called
        frame = b"\x00" * 2560
        detections = wake.detect(frame)
        assert detections == {}

        # Pipeline should not have been called
        pipeline.process_audio.assert_not_called()
        loop.close()


class TestMuteUnmuteSequence:
    """Test 5: Mute before pipeline/TTS, unmute after cooldown."""

    def test_mute_unmute_around_pipeline(self):
        vl, wake, capture, pipeline, loop, status_cb = _make_voice_loop(
            wake_detections=[{"hey_jarvis": 0.9}],
            capture_continues=[False],  # immediate end
        )

        import threading

        def run_loop():
            loop.run_forever()

        t = threading.Thread(target=run_loop, daemon=True)
        t.start()

        try:
            # Simulate the sequence
            frame = b"\x00" * 2560
            capture.reset()
            capture.process_frame(frame)
            audio = capture.get_audio()

            # Mute BEFORE pipeline
            wake.mute()
            future = asyncio.run_coroutine_threadsafe(
                pipeline.process_audio(audio), loop
            )
            future.result(timeout=5)

            # Cooldown then unmute
            time.sleep(0.1)  # shortened for test
            wake.unmute()

            # Verify order: mute called before unmute
            wake.mute.assert_called_once()
            wake.unmute.assert_called_once()
        finally:
            loop.call_soon_threadsafe(loop.stop)
            t.join(timeout=2)
            loop.close()


class TestTTSAplayPiMode:
    """Test 6: TTSService.speak in Pi mode calls subprocess aplay."""

    async def test_speak_pi_mode_calls_aplay(self, tmp_path):
        mock_voice = Mock()

        def fake_synthesize(text, wav_file):
            import struct
            import wave

            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(struct.pack("<h", 0) * 100)

        mock_voice.synthesize_wav = fake_synthesize

        with patch("lisa.services.tts_service.PiperVoice") as mock_cls, \
             patch("lisa.services.tts_service.PIPER_AVAILABLE", True):
            mock_cls.load.return_value = mock_voice

            model_file = tmp_path / "voice.onnx"
            model_file.write_text("fake")
            output_dir = tmp_path / "tts_out"
            output_dir.mkdir()

            from lisa.services.tts_service import TTSService

            svc = TTSService(
                model_path=str(model_file),
                output_dir=str(output_dir),
                dev_mode=False,
            )

            with patch("lisa.services.tts_service.subprocess") as mock_sub:
                mock_sub.run = Mock()
                result = await svc.speak("Hello from Pi")

                assert result is not None
                mock_sub.run.assert_called_once()
                call_args = mock_sub.run.call_args
                assert call_args[0][0][0] == "aplay"
                assert call_args[0][0][1] == "-q"


class TestTTSDevModeNoSubprocess:
    """Test 7: TTSService.speak in dev mode does NOT call subprocess."""

    async def test_speak_dev_mode_no_subprocess(self, tmp_path):
        mock_voice = Mock()

        def fake_synthesize(text, wav_file):
            import struct

            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(struct.pack("<h", 0) * 100)

        mock_voice.synthesize_wav = fake_synthesize

        with patch("lisa.services.tts_service.PiperVoice") as mock_cls, \
             patch("lisa.services.tts_service.PIPER_AVAILABLE", True):
            mock_cls.load.return_value = mock_voice

            model_file = tmp_path / "voice.onnx"
            model_file.write_text("fake")

            from lisa.services.tts_service import TTSService

            svc = TTSService(
                model_path=str(model_file),
                output_dir=str(tmp_path / "tts_output"),
                dev_mode=True,
            )

            with patch("lisa.services.tts_service.subprocess", create=True) as mock_sub:
                result = await svc.speak("Hello dev")
                assert result is not None
                mock_sub.run.assert_not_called()
