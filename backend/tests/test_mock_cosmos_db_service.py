"""Unit tests for MockCosmosDBService."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from app.models.config_options import CosmosDBOptions, MockCosmosProviderOptions, MockOptions
from app.services.mock_cosmos_db_service import MockCosmosDBService, MOCK_DATA_DIR


def _make_settings(
    mock_opts: MockOptions | None = None,
    cosmos_opts: CosmosDBOptions | None = None,
) -> MagicMock:
    """Create a mock Settings object with given options."""
    settings = MagicMock()
    type(settings).mock_options = PropertyMock(
        return_value=mock_opts or MockOptions()
    )
    type(settings).cosmos_db_options = PropertyMock(
        return_value=cosmos_opts or CosmosDBOptions()
    )
    return settings


@pytest.mark.unit
class TestEnsureClient:
    """Test _ensure_client connection priority and error handling."""

    def test_prefers_mock_connection_string(self):
        """Mock-specific connection_string takes priority over main Cosmos."""
        settings = _make_settings(
            mock_opts=MockOptions(
                cosmos=MockCosmosProviderOptions(
                    connection_string="AccountEndpoint=https://mock.documents.azure.com:443/;AccountKey=mock==;"
                )
            ),
            cosmos_opts=CosmosDBOptions(
                endpoint="https://main.documents.azure.com:443/"
            ),
        )
        service = MockCosmosDBService(settings=settings, logger=logging.getLogger("test"))

        with patch("app.services.mock_cosmos_db_service.CosmosClient") as MockClient:
            mock_instance = MagicMock()
            MockClient.from_connection_string.return_value = mock_instance

            result = service._ensure_client()

            MockClient.from_connection_string.assert_called_once()
            assert result is mock_instance

    def test_prefers_mock_endpoint_over_main(self):
        """Mock-specific endpoint takes priority over main Cosmos endpoint."""
        settings = _make_settings(
            mock_opts=MockOptions(
                cosmos=MockCosmosProviderOptions(
                    endpoint="https://mock.documents.azure.com:443/"
                )
            ),
            cosmos_opts=CosmosDBOptions(
                endpoint="https://main.documents.azure.com:443/"
            ),
        )
        service = MockCosmosDBService(settings=settings, logger=logging.getLogger("test"))

        with (
            patch("app.services.mock_cosmos_db_service.CosmosClient") as MockClient,
            patch("app.services.mock_cosmos_db_service.DefaultAzureCredential"),
        ):
            mock_instance = MagicMock()
            MockClient.return_value = mock_instance

            result = service._ensure_client()

            MockClient.assert_called_once()
            call_args = MockClient.call_args
            assert "mock.documents.azure.com" in call_args[0][0]
            assert result is mock_instance

    def test_falls_back_to_main_endpoint(self):
        """When no mock-specific settings, falls back to main Cosmos."""
        settings = _make_settings(
            mock_opts=MockOptions(),
            cosmos_opts=CosmosDBOptions(
                endpoint="https://main.documents.azure.com:443/"
            ),
        )
        service = MockCosmosDBService(settings=settings, logger=logging.getLogger("test"))

        with (
            patch("app.services.mock_cosmos_db_service.CosmosClient") as MockClient,
            patch("app.services.mock_cosmos_db_service.DefaultAzureCredential"),
        ):
            mock_instance = MagicMock()
            MockClient.return_value = mock_instance

            result = service._ensure_client()

            MockClient.assert_called_once()
            call_args = MockClient.call_args
            assert "main.documents.azure.com" in call_args[0][0]
            assert result is mock_instance

    def test_raises_when_nothing_configured(self):
        """Raises ValueError when no endpoint or connection_string at all."""
        settings = _make_settings(
            mock_opts=MockOptions(),
            cosmos_opts=CosmosDBOptions(),
        )
        service = MockCosmosDBService(settings=settings, logger=logging.getLogger("test"))

        with pytest.raises(ValueError, match="not configured"):
            service._ensure_client()

    def test_client_cached_on_second_call(self):
        """Client is created once and reused on subsequent calls."""
        settings = _make_settings(
            mock_opts=MockOptions(
                cosmos=MockCosmosProviderOptions(
                    connection_string="AccountEndpoint=https://mock.documents.azure.com:443/;AccountKey=x==;"
                )
            ),
        )
        service = MockCosmosDBService(settings=settings, logger=logging.getLogger("test"))

        with patch("app.services.mock_cosmos_db_service.CosmosClient") as MockClient:
            mock_instance = MagicMock()
            MockClient.from_connection_string.return_value = mock_instance

            first = service._ensure_client()
            second = service._ensure_client()

            assert first is second
            MockClient.from_connection_string.assert_called_once()


@pytest.mark.unit
class TestLoadInitialData:
    """Test seed data loading logic."""

    def test_load_calls_upsert_not_create(self):
        """Verify _load_json_into_container uses upsert_item (idempotent)."""
        settings = _make_settings(
            mock_opts=MockOptions(
                cosmos=MockCosmosProviderOptions(
                    connection_string="AccountEndpoint=https://t.documents.azure.com:443/;AccountKey=x==;"
                )
            ),
        )
        service = MockCosmosDBService(settings=settings, logger=logging.getLogger("test"))

        mock_container = AsyncMock()

        fsg_json = MOCK_DATA_DIR / "fsg.json"
        if fsg_json.exists():
            asyncio.run(
                service._load_json_into_container(
                    json_path=fsg_json,
                    container=mock_container,
                    label="FSG",
                )
            )
            assert mock_container.upsert_item.await_count > 0
            # Confirm create_item was never called
            mock_container.create_item.assert_not_awaited()

    def test_load_missing_file_warns(self):
        """Missing seed file logs warning and doesn't raise."""
        settings = _make_settings(
            mock_opts=MockOptions(
                cosmos=MockCosmosProviderOptions(
                    connection_string="AccountEndpoint=https://t.documents.azure.com:443/;AccountKey=x==;"
                )
            ),
        )
        test_logger = logging.getLogger("test_missing")
        service = MockCosmosDBService(settings=settings, logger=test_logger)

        mock_container = AsyncMock()
        from pathlib import Path

        fake_path = Path("/nonexistent/file.json")

        with patch.object(test_logger, "warning") as mock_warn:
            asyncio.run(
                service._load_json_into_container(
                    json_path=fake_path,
                    container=mock_container,
                    label="Test",
                )
            )
            mock_warn.assert_called_once()
            assert "not found" in mock_warn.call_args[0][0].lower()

        mock_container.upsert_item.assert_not_awaited()
