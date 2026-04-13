import pytest
import os
import tempfile

# Create a temporary database file for tests (in-memory :memory: creates
# independent databases per connection, which breaks cross-connection table access)
_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_test_db_path = _test_db.name
_test_db.close()

os.environ["LISA_DEV_MODE"] = "true"
os.environ["LISA_DB_PATH"] = _test_db_path
# Force dummy API keys so the session safety net does not trip on .env values.
# Any key not prefixed with "sk-ant-" is allowed through by the live-key guard.
os.environ["LISA_ANTHROPIC_API_KEY"] = "test-key-123"
os.environ["LISA_OPENAI_API_KEY"] = "test-key-123"

from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager
from lisa.main import app
from lisa.device.fake_adapter import FakeAdapter


# -- Safety net: fail any test that constructs AsyncAnthropic with a live key --
#
# Dummy keys (anything not starting with "sk-ant-") pass through so unit tests
# that use "test-key-123" keep working. Live keys raise RuntimeError so we catch
# accidental live Anthropic calls before they burn credits or hang offline runs.
@pytest.fixture(autouse=True, scope="session")
def _fail_on_live_anthropic_key():
    import anthropic

    original_init = anthropic.AsyncAnthropic.__init__

    def patched_init(self, *args, **kwargs):
        api_key = kwargs.get("api_key")
        if isinstance(api_key, str) and api_key.startswith("sk-ant-"):
            raise RuntimeError(
                "Live Anthropic key detected in test run. "
                "Use the mock_llm_intent fixture or a dummy key."
            )
        return original_init(self, *args, **kwargs)

    mp = pytest.MonkeyPatch()
    mp.setattr(anthropic.AsyncAnthropic, "__init__", patched_init)
    try:
        yield
    finally:
        mp.undo()


@pytest.fixture
def fake_adapter():
    return FakeAdapter()


@pytest.fixture
async def client():
    """Async test client with app lifespan properly triggered."""
    # Clean the database before each test
    if os.path.exists(_test_db_path):
        os.unlink(_test_db_path)
    async with LifespanManager(app) as manager:
        transport = ASGITransport(app=manager.app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
def mock_llm_intent(monkeypatch):
    """Mock LLMIntentService.parse_intent to route responses by input text.

    Returns a helper object with .set_response(text, intent=None, raise_=None).
    Default fallback returns an IntentResult with intent=None (unknown intent).

    Usage:
        def test_foo(mock_llm_intent):
            mock_llm_intent.set_response(
                "turn on the bedroom lamp",
                intent=DeviceIntent(device_id="fake-lamp-1", action="turn_on",
                                    confirmation="Turning on the bedroom lamp"),
            )
    """
    # Lazy import: IntentResult does not exist until Task 2 lands. Importing
    # at fixture-use time keeps conftest collectible even if Task 2 is absent,
    # and only fails when a test actually requests this fixture.
    from lisa.services.llm_intent_service import IntentResult  # noqa: E402

    class _MockHelper:
        def __init__(self):
            self._responses: dict = {}

        def set_response(self, text, intent=None, raise_=None):
            self._responses[text] = (intent, raise_)

    helper = _MockHelper()

    async def fake_parse_intent(self, text, devices):
        if text in helper._responses:
            stored_intent, raise_ = helper._responses[text]
            if raise_ is not None:
                raise raise_
            return IntentResult(
                intent=stored_intent,
                debug={
                    "input_text": text,
                    "devices_seen": devices,
                    "decision": {
                        "tool_used": stored_intent is not None,
                        **(
                            {
                                "device_id": stored_intent.device_id,
                                "action": stored_intent.action,
                                "confirmation": stored_intent.confirmation,
                            }
                            if stored_intent is not None
                            else {"text": "mock response"}
                        ),
                    },
                    "usage": {"input_tokens": 0, "output_tokens": 0},
                    "stop_reason": "end_turn",
                },
            )
        # Default: unknown intent
        return IntentResult(
            intent=None,
            debug={
                "input_text": text,
                "devices_seen": devices,
                "decision": {
                    "tool_used": False,
                    "text": "default mock: unknown intent",
                },
                "usage": {"input_tokens": 0, "output_tokens": 0},
                "stop_reason": "end_turn",
            },
        )

    monkeypatch.setattr(
        "lisa.services.llm_intent_service.LLMIntentService.parse_intent",
        fake_parse_intent,
    )
    yield helper
