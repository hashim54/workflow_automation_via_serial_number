"""Configuration options for all Azure services and application settings."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CosmosDBOptions(BaseModel):
    """Configuration for Azure Cosmos DB for workflow persistence.

    Supports two authentication methods:
    1. Managed Identity (recommended): Set endpoint only, uses DefaultAzureCredential
    2. Connection String (dev/test only): Set connection_string
    """

    endpoint: Optional[str] = Field(
        default=None, description="Cosmos DB endpoint URL (e.g., https://<account>.documents.azure.com:443/)"
    )
    connection_string: Optional[str] = Field(
        default=None, description="Cosmos DB connection string (dev/test only - not recommended for production)"
    )
    database_name: str = Field(default="workflow-db", min_length=1, description="Database name for storing workflows")
    container_name: str = Field(default="workflows", min_length=1, description="Container name for workflow records")
    partition_key_paths: list[str] = Field(
        default=["/user_id", "/serial_number"],
        description="Hierarchical Partition Key paths (HPK): first level user_id, second level serial_number",
    )
    enable_ttl: bool = Field(default=True, description="Enable TTL on the container to auto-expire records")
    default_ttl_days: int = Field(default=30, description="Default TTL in days for workflow records")

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, v: Optional[str]) -> Optional[str]:
        """Validate Cosmos DB endpoint format if provided."""
        if v and not v.startswith("https://"):
            raise ValueError("Cosmos DB endpoint must start with https://")
        return v

    model_config = {
        "str_strip_whitespace": True,
    }


class BlobStorageOptions(BaseModel):
    """Configuration for Azure Blob Storage for artifact storage.

    Supports two authentication methods:
    1. Managed Identity (recommended): Set account_url only, uses DefaultAzureCredential
    2. Connection String (dev/test only): Set connection_string
    """

    account_url: Optional[str] = Field(
        default=None, description="Azure Storage Account URL (e.g., https://<account>.blob.core.windows.net/)"
    )
    connection_string: Optional[str] = Field(
        default=None, description="Azure Storage connection string (dev/test only - not recommended for production)"
    )
    artifacts_container: str = Field(
        default="artifacts", min_length=1, description="Container name for workflow artifacts (images, documents)"
    )

    @field_validator("account_url")
    @classmethod
    def validate_account_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate Storage Account URL format if provided."""
        if v and not v.startswith("https://"):
            raise ValueError("Storage Account URL must start with https://")
        return v

    model_config = {
        "str_strip_whitespace": True,
    }


class FoundryOptions(BaseModel):
    """Configuration for Microsoft Foundry service.

    Microsoft Foundry hosts AI agents and provides agent orchestration capabilities.
    Uses DefaultAzureCredential for authentication.
    """

    project_endpoint: str = Field(..., min_length=1, description="Microsoft Foundry project endpoint URL")
    image_processing_agent_id: str = Field(
        ..., min_length=1, description="Agent ID for image processing (extracts serial numbers from images)"
    )
    reasoning_agent_id: str = Field(
        ..., min_length=1, description="Agent ID for reasoning and analysis (generates recommendations)"
    )
    image_processing_temperature: float = Field(
        default=0.1, ge=0.0, le=2.0, description="Temperature for image processing agent (lower = more deterministic)"
    )
    image_processing_max_tokens: int = Field(
        default=2048, gt=0, description="Maximum tokens for image processing agent responses"
    )
    reasoning_temperature: float = Field(
        default=0.3, ge=0.0, le=2.0, description="Temperature for reasoning agent (higher = more creative analysis)"
    )
    reasoning_max_tokens: int = Field(default=4096, gt=0, description="Maximum tokens for reasoning agent responses")

    model_config = {
        "str_strip_whitespace": True,
    }


class ApplicationInsightsOptions(BaseModel):
    """Configuration for Azure Application Insights telemetry.

    Application Insights provides monitoring, distributed tracing, and diagnostics
    for production applications.
    """

    connection_string: Optional[str] = Field(
        default=None,
        description="Application Insights connection string (e.g., InstrumentationKey=...;IngestionEndpoint=...)",
    )
    enabled: bool = Field(default=True, description="Enable Application Insights telemetry collection")
    sampling_percentage: float = Field(
        default=100.0,
        ge=0.0,
        le=100.0,
        description="Sampling percentage for telemetry (100 = all, lower reduces ingestion costs)",
    )

    model_config = {
        "str_strip_whitespace": True,
    }


class MCPClientOptions(BaseModel):
    """Configuration for MCP (Model Context Protocol) client endpoints.

    MCP clients invoke deterministic API calls to external services
    (FSG, Phoenix) via Azure API Management.
    """

    fsg_endpoint: Optional[str] = Field(
        default=None, description="FSG (Field Service Gateway) MCP endpoint URL via Azure APIM"
    )
    phoenix_endpoint: Optional[str] = Field(
        default=None, description="Phoenix MCP endpoint URL via Azure APIM"
    )
    timeout_seconds: int = Field(
        default=30, ge=1, le=300, description="HTTP timeout for MCP client requests in seconds"
    )
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum number of retries for failed MCP requests")

    @field_validator("fsg_endpoint", "phoenix_endpoint")
    @classmethod
    def validate_endpoint_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate MCP endpoint URL format if provided."""
        if v and not v.startswith("https://"):
            raise ValueError("MCP endpoint must start with https://")
        return v or None

    model_config = {
        "str_strip_whitespace": True,
    }


class WorkflowOptions(BaseModel):
    """Configuration for workflow execution behavior.

    Controls execution parameters, timeouts, and feature flags.
    """

    max_execution_time_seconds: int = Field(
        default=300, ge=10, le=3600, description="Maximum workflow execution time in seconds (timeout)"
    )
    enable_image_processing: bool = Field(default=True, description="Enable image processing agent for image inputs")
    enable_parallel_mcp_calls: bool = Field(
        default=False, description="Execute FSG and Phoenix MCP calls in parallel (experimental)"
    )

    model_config = {
        "str_strip_whitespace": True,
    }


class APIOptions(BaseModel):
    """Configuration for the FastAPI server.

    Controls server binding, CORS, rate limiting, and API documentation.
    """

    host: str = Field(
        default="0.0.0.0", description="API server host (0.0.0.0 for all interfaces, 127.0.0.1 for localhost only)"
    )
    port: int = Field(default=8000, ge=1, le=65535, description="API server port number")

    # CORS settings
    enable_cors: bool = Field(default=True, description="Enable CORS (Cross-Origin Resource Sharing)")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"],
        description="Allowed CORS origins",
    )

    # API documentation
    enable_docs: bool = Field(default=True, description="Enable Swagger/OpenAPI documentation endpoints")

    # Rate limiting
    enable_rate_limiting: bool = Field(default=False, description="Enable rate limiting per user/IP")
    rate_limit_per_minute: int = Field(
        default=60, ge=1, le=1000, description="Maximum requests per user per minute (when rate limiting enabled)"
    )

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port is within valid range."""
        if v < 1 or v > 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    model_config = {
        "str_strip_whitespace": True,
    }


class KeyVaultOptions(BaseModel):
    """Configuration for Azure Key Vault for secrets management.

    When enabled, sensitive settings (connection strings, API keys) are resolved
    from Key Vault instead of environment variables. Uses DefaultAzureCredential
    (managed identity in production, developer credentials locally).
    """

    url: Optional[str] = Field(
        default=None, description="Key Vault URL (e.g., https://<vault>.vault.azure.net/)"
    )
    use_key_vault: bool = Field(default=False, description="Enable Key Vault for secrets resolution")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate Key Vault URL format if provided."""
        if v and not v.startswith("https://"):
            raise ValueError("Key Vault URL must start with https://")
        return v

    model_config = {
        "str_strip_whitespace": True,
    }
