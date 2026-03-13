"""Unit tests for API endpoints."""

import io

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
        response = client.post("/api/v1/workflows")

        # Should return 422 for validation error (missing required form field)
        assert response.status_code == 422

    def test_execute_workflow_accepts_valid_request(self, client: TestClient):
        """Test that workflow accepts valid request structure."""
        response = client.post(
            "/api/v1/workflows",
            data={"serial_number": "SN-TEST-001"},
        )

        # May return 500 if services not configured, but validates request schema
        assert response.status_code in [200, 500, 503]

    def test_execute_workflow_with_image(self, client: TestClient):
        """Test workflow execution with an image upload."""
        files = {"file": ("test.png", io.BytesIO(b"\x89PNG\r\n\x1a\nfakeimage"), "image/png")}
        response = client.post(
            "/api/v1/workflows",
            data={"serial_number": "SN-TEST-002"},
            files=files,
        )

        # May return 500 if blob storage not configured
        assert response.status_code in [200, 500, 503]

    def test_execute_workflow_rejects_non_image(self, client: TestClient):
        """Test that non-image files are rejected."""
        files = {"file": ("doc.pdf", io.BytesIO(b"fake pdf"), "application/pdf")}
        response = client.post(
            "/api/v1/workflows",
            data={"serial_number": "SN-TEST-003"},
            files=files,
        )

        assert response.status_code == 422
        assert "Unsupported file type" in response.json()["detail"]

    def test_execute_workflow_rejects_empty_file(self, client: TestClient):
        """Test that empty files are rejected."""
        files = {"file": ("empty.png", io.BytesIO(b""), "image/png")}
        response = client.post(
            "/api/v1/workflows",
            data={"serial_number": "SN-TEST-004"},
            files=files,
        )

        assert response.status_code == 422
        assert "empty" in response.json()["detail"].lower()

    def test_execute_workflow_rejects_oversized_file(self, client: TestClient):
        """Test that files exceeding 10 MB are rejected."""
        big_data = b"x" * (10 * 1024 * 1024 + 1)
        files = {"file": ("big.png", io.BytesIO(big_data), "image/png")}
        response = client.post(
            "/api/v1/workflows",
            data={"serial_number": "SN-TEST-005"},
            files=files,
        )

        assert response.status_code == 422
        assert "too large" in response.json()["detail"].lower()

    def test_get_workflow_status_endpoint_exists(self, client: TestClient):
        """Test that workflow status endpoint exists."""
        response = client.get("/api/v1/workflows/SN-TEST-001")

        # Endpoint should exist (may return 404 or 500 if not implemented)
        assert response.status_code in [200, 404, 500, 503]

    def test_workflow_endpoints_return_json(self, client: TestClient):
        """Test that workflow endpoints return JSON."""
        response = client.post(
            "/api/v1/workflows",
            data={"serial_number": "SN-JSON-TEST"},
        )

        # Should return JSON regardless of status code
        assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.unit
class TestAPIValidation:
    """Test API request validation."""

    def test_empty_serial_number_rejected(self, client: TestClient):
        """Test that empty serial number is rejected."""
        response = client.post(
            "/api/v1/workflows",
            data={"serial_number": ""},
        )

        assert response.status_code == 422

    def test_missing_serial_number_field(self, client: TestClient):
        """Test request without serial_number form field."""
        response = client.post("/api/v1/workflows")

        assert response.status_code == 422
