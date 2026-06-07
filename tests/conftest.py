"""
pytest conftest — shared fixtures for SkyView tests.
"""

import os
import pytest
from fastapi.testclient import TestClient

# Use SQLite in-memory for tests — no PostgreSQL needed
os.environ.setdefault("DATABASE_URL", "sqlite:///test_skyview.db")
os.environ.setdefault("GROQ_API_KEY", "test_key")
os.environ.setdefault("DEBUG", "True")

from skyview.main import app  # noqa: E402 — env must be set before import


@pytest.fixture(scope="session")
def client():
    """Synchronous test client for the full SkyView FastAPI app."""
    with TestClient(app) as c:
        yield c