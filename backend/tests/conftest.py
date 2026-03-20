"""Pytest configuration and shared fixtures."""

import os

import pytest
from fastapi.testclient import TestClient

# Load test environment before importing app
os.environ["ENV_FILE"] = ".env.test"
# Ensure mock API is disabled in the default test client
os.environ.setdefault("MOCK_ENABLED", "false")

from app.api.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)
