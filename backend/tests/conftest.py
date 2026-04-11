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

from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager
from lisa.main import app
from lisa.device.fake_adapter import FakeAdapter


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
