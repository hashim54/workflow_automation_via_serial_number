"""Unit tests for mock API routes (/mock-api/...)."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.mock_api import router as mock_router
from app.services.mock_cosmos_db_service import MockCosmosDBService


@pytest.mark.unit
class TestMockRoutesDisabled:
    """Verify mock routes are NOT registered when COSMOS_MOCK_ENABLED=false.

    The default test app (conftest.py) does NOT enable mock, so these routes
    should not exist.
    """

    def test_fsg_route_not_found_when_disabled(self, client: TestClient):
        """GET /mock-api/fsg/products/X returns 404 when mock is disabled."""
        response = client.get("/mock-api/fsg/products/30691602340734")
        assert response.status_code == 404

    def test_phoenix_route_not_found_when_disabled(self, client: TestClient):
        """GET /mock-api/phoenix/plm/serialnumber/X returns 404 when mock is disabled."""
        response = client.get("/mock-api/phoenix/plm/serialnumber/30691600035")
        assert response.status_code == 404


def _create_mock_enabled_app(mock_service: MockCosmosDBService) -> FastAPI:
    """Create a minimal FastAPI app with mock routes and an injected mock service."""
    app = FastAPI()
    app.include_router(mock_router, prefix="/mock-api")

    # Override the DI dependency with our mock service
    from app.api.routes.mock_api import _get_mock_cosmos

    app.dependency_overrides[_get_mock_cosmos] = lambda: mock_service
    return app


@pytest.mark.unit
class TestMockRoutesEnabled:
    """Verify mock routes delegate to MockCosmosDBService correctly."""

    def test_fsg_product_found(self):
        """GET /mock-api/fsg/products/{sn} returns 200 with payload when found."""
        fake_doc = {"id": "fsg_123", "serial_number": "123", "payload": {"warranty": "active"}}
        service = AsyncMock(spec=MockCosmosDBService)
        service.get_fsg_product.return_value = fake_doc

        app = _create_mock_enabled_app(service)
        client = TestClient(app)

        response = client.get("/mock-api/fsg/products/123")
        assert response.status_code == 200
        assert response.json() == {"warranty": "active"}

    def test_fsg_product_not_found(self):
        """GET /mock-api/fsg/products/{sn} returns 404 when not found."""
        service = AsyncMock(spec=MockCosmosDBService)
        service.get_fsg_product.return_value = None

        app = _create_mock_enabled_app(service)
        client = TestClient(app)

        response = client.get("/mock-api/fsg/products/MISSING")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_phoenix_product_found(self):
        """GET /mock-api/phoenix/plm/serialnumber/{pn} returns 200 with payload."""
        fake_doc = {
            "id": "phoenix_456",
            "lookup_product_input_product_number": "456",
            "payload": {"model": "XYZ"},
        }
        service = AsyncMock(spec=MockCosmosDBService)
        service.get_phoenix_product.return_value = fake_doc

        app = _create_mock_enabled_app(service)
        client = TestClient(app)

        response = client.get("/mock-api/phoenix/plm/serialnumber/456")
        assert response.status_code == 200
        assert response.json() == {"model": "XYZ"}

    def test_phoenix_product_not_found(self):
        """GET /mock-api/phoenix/plm/serialnumber/{pn} returns 404 when not found."""
        service = AsyncMock(spec=MockCosmosDBService)
        service.get_phoenix_product.return_value = None

        app = _create_mock_enabled_app(service)
        client = TestClient(app)

        response = client.get("/mock-api/phoenix/plm/serialnumber/MISSING")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_fsg_returns_full_doc_when_no_payload_key(self):
        """When document has no 'payload' key, return the full document."""
        fake_doc = {"id": "fsg_999", "serial_number": "999", "data": "raw"}
        service = AsyncMock(spec=MockCosmosDBService)
        service.get_fsg_product.return_value = fake_doc

        app = _create_mock_enabled_app(service)
        client = TestClient(app)

        response = client.get("/mock-api/fsg/products/999")
        assert response.status_code == 200
        assert response.json() == fake_doc
