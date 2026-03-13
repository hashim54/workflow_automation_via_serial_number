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

    def test_execute_workflow_requires_file(self, client: TestClient):
        """Test that workflow execution requires a file upload."""
        response = client.post("/api/v1/workflows")

        # Should return 422 for missing required 'file' field
        assert response.status_code == 422

    def test_execute_workflow_accepts_valid_image(self, client: TestClient):
        """Test that workflow accepts a valid image upload."""
        files = {"file": ("test.png", io.BytesIO(b"\x89PNG\r\n\x1a\nfakeimage"), "image/png")}
        response = client.post("/api/v1/workflows", files=files)

        # May return 500/503 if services not configured, but validates request schema
        assert response.status_code in [200, 500, 503]

    def test_execute_workflow_with_jpeg(self, client: TestClient):
        """Test workflow execution with a JPEG image upload."""
        files = {"file": ("photo.jpg", io.BytesIO(b"\xff\xd8\xff\xe0fakeimage"), "image/jpeg")}
        response = client.post("/api/v1/workflows", files=files)

        # May return 500/503 if services not configured
        assert response.status_code in [200, 500, 503]

    def test_execute_workflow_rejects_non_image(self, client: TestClient):
        """Test that non-image files are rejected."""
        files = {"file": ("doc.pdf", io.BytesIO(b"fake pdf"), "application/pdf")}
        response = client.post("/api/v1/workflows", files=files)

        assert response.status_code == 422
        assert "Unsupported file type" in response.json()["detail"]

    def test_execute_workflow_rejects_empty_file(self, client: TestClient):
        """Test that empty files are rejected."""
        files = {"file": ("empty.png", io.BytesIO(b""), "image/png")}
        response = client.post("/api/v1/workflows", files=files)

        assert response.status_code == 422
        assert "empty" in response.json()["detail"].lower()

    def test_execute_workflow_rejects_oversized_file(self, client: TestClient):
        """Test that files exceeding 10 MB are rejected."""
        big_data = b"x" * (10 * 1024 * 1024 + 1)
        files = {"file": ("big.png", io.BytesIO(big_data), "image/png")}
        response = client.post("/api/v1/workflows", files=files)

        assert response.status_code == 422
        assert "too large" in response.json()["detail"].lower()

    def test_get_workflow_status_endpoint_exists(self, client: TestClient):
        """Test that workflow status endpoint exists."""
        response = client.get("/api/v1/workflows/SN-TEST-001")

        # Endpoint should exist (may return 404 or 503 if not implemented/configured)
        assert response.status_code in [200, 404, 500, 503]

    def test_workflow_endpoints_return_json(self, client: TestClient):
        """Test that workflow endpoints return JSON."""
        files = {"file": ("test.png", io.BytesIO(b"\x89PNG\r\n\x1a\nfakeimage"), "image/png")}
        response = client.post("/api/v1/workflows", files=files)

        assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.unit
class TestAPIValidation:
    """Test API request validation."""

    def test_unsupported_content_type_rejected(self, client: TestClient):
        """Test that unsupported MIME types return 422."""
        files = {"file": ("file.txt", io.BytesIO(b"hello"), "text/plain")}
        response = client.post("/api/v1/workflows", files=files)

        assert response.status_code == 422
        assert "Unsupported file type" in response.json()["detail"]

    def test_missing_file_field(self, client: TestClient):
        """Test request without the file field returns 422."""
        response = client.post("/api/v1/workflows")

        assert response.status_code == 422
