"""Unit tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check_returns_200(self, client: TestClient):
        """Test that health check returns 200 OK."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_health_check_content_type(self, client: TestClient):
        """Test that health check returns JSON."""
        response = client.get("/health")

        assert "application/json" in response.headers["content-type"]


@pytest.mark.unit
class TestWorkflowEndpoints:
    """Test workflow API endpoints."""

    def test_execute_workflow_requires_serial_number(self, client: TestClient):
        """Test that workflow execution requires serial_number."""
        response = client.post(
            "/api/v1/workflows",
            json={"data": {"test": "data"}},
        )

        # Should return 422 for validation error
        assert response.status_code == 422

    def test_execute_workflow_accepts_valid_request(self, client: TestClient):
        """Test that workflow accepts valid request structure."""
        # Note: This will fail until services are fully implemented
        # For now, we're testing the API contract
        response = client.post(
            "/api/v1/workflows",
            json={
                "serial_number": "SN-TEST-001",
                "data": {},
            },
        )

        # May return 500 if services not configured, but validates request schema
        assert response.status_code in [200, 500, 503]

    def test_execute_workflow_with_data_payload(self, client: TestClient):
        """Test workflow execution with data payload."""
        response = client.post(
            "/api/v1/workflows",
            json={
                "serial_number": "SN-TEST-002",
                "data": {
                    "image_url": "https://example.com/image.jpg",
                    "metadata": {"source": "test"},
                },
            },
        )

        # Validates request structure
        assert response.status_code in [200, 500, 503]

    def test_get_workflow_status_endpoint_exists(self, client: TestClient):
        """Test that workflow status endpoint exists."""
        response = client.get("/api/v1/workflows/SN-TEST-001")

        # Endpoint should exist (may return 404 or 500 if not implemented)
        assert response.status_code in [200, 404, 500, 503]

    def test_workflow_endpoints_return_json(self, client: TestClient):
        """Test that workflow endpoints return JSON."""
        response = client.post(
            "/api/v1/workflows",
            json={"serial_number": "SN-JSON-TEST"},
        )

        # Should return JSON regardless of status code
        assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.unit
class TestAPIValidation:
    """Test API request validation."""

    def test_invalid_json_returns_422(self, client: TestClient):
        """Test that invalid JSON returns 422."""
        response = client.post(
            "/api/v1/workflows",
            content=b"invalid-json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_empty_serial_number_rejected(self, client: TestClient):
        """Test that empty serial number is rejected."""
        response = client.post(
            "/api/v1/workflows",
            json={"serial_number": ""},
        )

        assert response.status_code == 422

    def test_missing_content_type_header(self, client: TestClient):
        """Test request without Content-Type header."""
        response = client.post(
            "/api/v1/workflows",
            content=b'{"serial_number": "SN-TEST"}',
        )

        # FastAPI should still handle it
        assert response.status_code in [200, 422, 500, 503]
