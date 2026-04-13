• Use two terminals.


  .\.venv\Scripts\python.exe -m uvicorn lisa.main:app --host 127.0.0.1 --port 8001 --reload

  If you want the backend to read a local env file first, create it once:

  Copy-Item .env.example .env

  You can leave LISA_DEV_MODE=true. With no API keys set, local typed commands still work through the fallback parser.

  Dashboard
  From E:\dev\lisa\dashboard:

  npm run dev

  If npm run dev complains about missing deps:

  npm install
  npm run dev

  Smoke Test

  1. Open http://localhost:5173.
  2. Confirm you see fake devices. The tests expect 3 devices and one is Bedroom Lamp.
  3. In the text command box, send:
      - turn on the bedroom lamp
      - turn off the bedroom lamp
  4. Confirm:
      - command returns success
      - device state flips on/off
      - command history updates
  5. Send a bad command like what is the weather and confirm you get a rejected/logged result.

  Direct API Test
  If you want to test without the UI:

  Invoke-RestMethod -Method Post `
    -Uri http://127.0.0.1:8001/api/commands/text `
    -ContentType 'application/json' `
    -Body '{"text":"turn on the bedroom lamp","source":"dashboard"}'

  Automated Tests
  From E:\dev\lisa\backend:

  .\.venv\Scripts\pytest.exe

  If you want the most useful subset first:

  Optional Full Pipeline Locally
  If you later want typed text to go through LLM + TTS locally, add these in backend\.env:

  - LISA_TTS_MODEL_PATH=... pointing to a local Piper .onnx model

  You still do not need a Pi for that. The Pi-only part is the always-on wake-word/microphone loop.

  If you want, I can give you a minimal backend\.env template for the “typed text + LLM + Piper” local setup.


› yeah sounds good


• Create /E:/dev/lisa/backend/.env like this:

  LISA_DEV_MODE=true
  LISA_DB_PATH=lisa.db
  LISA_HOST=127.0.0.1
  LISA_KASA_USERNAME=
  LISA_KASA_PASSWORD=

  LISA_OPENAI_API_KEY=
  LISA_ANTHROPIC_API_KEY=your_anthropic_key_here

  LISA_STT_MODEL=whisper-1
  LISA_STT_TIMEOUT=3.0

  LISA_LLM_MODEL=claude-haiku-4-5
  LISA_LLM_TIMEOUT=3.0

  LISA_TTS_MODEL_PATH=E:/models/piper/en_US-lessac-medium.onnx
  LISA_TTS_OUTPUT_DIR=tts_output

  For the local typed-command flow, the only fields you actually need are:

  - LISA_DEV_MODE=true
  - LISA_ANTHROPIC_API_KEY=...
  - LISA_TTS_MODEL_PATH=...

  You can leave LISA_OPENAI_API_KEY empty unless you start testing real audio/STT paths.

  Then restart the backend and test with:

  - turn on the bedroom lamp
  - turn off the bedroom lamp
  - what is the weather

  Expected behavior:

  - valid device commands go through LLM -> fake device -> TTS WAV output
  - unknown commands get rejected and logged
  - generated WAVs appear in backend/tts_output

  On Windows, use forward slashes in LISA_TTS_MODEL_PATH or escaped backslashes. If you want, I can also give you a quick way to
  obtain a compatible Piper .onnx model and verify it loads before you run the app.