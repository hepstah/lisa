import pytest
import os

# Use in-memory SQLite for tests
os.environ["LISA_DEV_MODE"] = "true"
os.environ["LISA_DB_PATH"] = ":memory:"
