"""Unit tests for configuration models and settings."""

import pytest
from app.models.config_options import (
    APIOptions,
    ApplicationInsightsOptions,
    BlobStorageOptions,
    CosmosDBOptions,
    MCPClientOptions,
    FoundryOptions,
    WorkflowOptions,
)
from pydantic import ValidationError


@pytest.mark.unit
class TestCosmosDBOptions:
    """Test CosmosDB configuration validation."""

    def test_valid_endpoint(self):
        """Test valid Cosmos DB endpoint."""
        config = CosmosDBOptions(
            endpoint="https://myaccount.documents.azure.com:443/",
            database_name="test-db",
            container_name="test-container",
        )
        assert config.endpoint == "https://myaccount.documents.azure.com:443/"

    def test_invalid_endpoint_scheme(self):
        """Test that non-https endpoint raises validation error."""
        with pytest.raises(ValidationError, match="must start with https://"):
            CosmosDBOptions(
                endpoint="http://myaccount.documents.azure.com:443/",
                database_name="test-db",
                container_name="test-container",
            )

    def test_connection_string_mode(self):
        """Test using connection string instead of endpoint."""
        config = CosmosDBOptions(
            connection_string="AccountEndpoint=https://test.documents.azure.com:443/;AccountKey=test==;",
            database_name="test-db",
            container_name="test-container",
        )
        assert config.connection_string is not None
        assert config.endpoint is None

    def test_defaults(self):
        """Test default values."""
        config = CosmosDBOptions(endpoint="https://test.documents.azure.com:443/")
        assert config.database_name == "workflow-db"
        assert config.container_name == "workflows"
        assert config.partition_key_paths == ["/user_id", "/serial_number"]
        assert config.enable_ttl is True
        assert config.default_ttl_days == 30


@pytest.mark.unit
class TestBlobStorageOptions:
    """Test Blob Storage configuration validation."""

    def test_valid_account_url(self):
        """Test valid storage account URL."""
        config = BlobStorageOptions(account_url="https://myaccount.blob.core.windows.net/")
        assert config.account_url == "https://myaccount.blob.core.windows.net/"

    def test_invalid_account_url_scheme(self):
        """Test that non-https URL raises validation error."""
        with pytest.raises(ValidationError, match="must start with https://"):
            BlobStorageOptions(account_url="http://myaccount.blob.core.windows.net/")

    def test_connection_string_mode(self):
        """Test using connection string."""
        config = BlobStorageOptions(
            connection_string="DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test==;"
        )
        assert config.connection_string is not None

    def test_defaults(self):
        """Test default container name."""
        config = BlobStorageOptions(account_url="https://test.blob.core.windows.net/")
        assert config.artifacts_container == "artifacts"


@pytest.mark.unit
class TestFoundryOptions:
    """Test Microsoft Foundry configuration validation."""

    def test_valid_config(self):
        """Test valid Foundry configuration with both agents."""
        config = FoundryOptions(
            project_endpoint="https://test.api.azureml.ms",
            image_processing_agent_id="agent-img-001",
            reasoning_agent_id="agent-reason-001",
        )
        assert config.image_processing_agent_id == "agent-img-001"
        assert config.reasoning_agent_id == "agent-reason-001"

    def test_temperature_defaults(self):
        """Test temperature default values."""
        config = FoundryOptions(
            project_endpoint="https://test.api.azureml.ms",
            image_processing_agent_id="img-001",
            reasoning_agent_id="reason-001",
        )
        assert config.image_processing_temperature == 0.1
        assert config.reasoning_temperature == 0.3

    def test_max_tokens_defaults(self):
        """Test max tokens default values."""
        config = FoundryOptions(
            project_endpoint="https://test.api.azureml.ms",
            image_processing_agent_id="img-001",
            reasoning_agent_id="reason-001",
        )
        assert config.image_processing_max_tokens == 2048
        assert config.reasoning_max_tokens == 4096

    def test_temperature_bounds(self):
        """Test temperature validation bounds."""
        with pytest.raises(ValidationError):
            FoundryOptions(
                project_endpoint="https://test.api.azureml.ms",
                image_processing_agent_id="img-001",
                reasoning_agent_id="reason-001",
                image_processing_temperature=-0.1,  # Invalid: < 0
            )

        with pytest.raises(ValidationError):
            FoundryOptions(
                project_endpoint="https://test.api.azureml.ms",
                image_processing_agent_id="img-001",
                reasoning_agent_id="reason-001",
                reasoning_temperature=2.5,  # Invalid: > 2.0
            )

    def test_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            FoundryOptions(  # type: ignore[call-arg]
                project_endpoint="https://test.api.azureml.ms",
                # Missing both agent IDs
            )


@pytest.mark.unit
class TestApplicationInsightsOptions:
    """Test Application Insights configuration."""

    def test_defaults(self):
        """Test default values."""
        config = ApplicationInsightsOptions()
        assert config.enabled is True
        assert config.sampling_percentage == 100.0

    def test_sampling_percentage_bounds(self):
        """Test sampling percentage validation."""
        config = ApplicationInsightsOptions(sampling_percentage=50.0)
        assert config.sampling_percentage == 50.0

        with pytest.raises(ValidationError):
            ApplicationInsightsOptions(sampling_percentage=-1.0)

        with pytest.raises(ValidationError):
            ApplicationInsightsOptions(sampling_percentage=101.0)


@pytest.mark.unit
class TestMCPClientOptions:
    """Test MCP client configuration."""

    def test_valid_config(self):
        """Test valid MCP client configuration."""
        config = MCPClientOptions(
            fsg_endpoint="https://apim.azure-api.net/fsg",
            phoenix_endpoint="https://apim.azure-api.net/phoenix",
        )
        assert config.fsg_endpoint == "https://apim.azure-api.net/fsg"
        assert config.phoenix_endpoint == "https://apim.azure-api.net/phoenix"

    def test_defaults(self):
        """Test default timeout and retry values."""
        config = MCPClientOptions(
            fsg_endpoint="https://test.com/fsg",
            phoenix_endpoint="https://test.com/phoenix",
        )
        assert config.timeout_seconds == 30
        assert config.max_retries == 3


@pytest.mark.unit
class TestWorkflowOptions:
    """Test workflow configuration."""

    def test_defaults(self):
        """Test default workflow settings."""
        config = WorkflowOptions()
        # Add assertions when workflow options are defined
        pass


@pytest.mark.unit
class TestAPIOptions:
    """Test API server configuration."""

    def test_defaults(self):
        """Test default API settings."""
        config = APIOptions()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.enable_cors is True
        assert config.enable_docs is True

    def test_custom_values(self):
        """Test custom API settings."""
        config = APIOptions(
            host="127.0.0.1",
            port=9000,
            enable_cors=False,
            enable_docs=False,
        )
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.enable_cors is False
        assert config.enable_docs is False
