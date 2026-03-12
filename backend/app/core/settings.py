"""
Unified settings loader with Pydantic validation.

Loads configuration from (highest → lowest priority):
1. Constructor kwargs (test overrides)
2. Environment variables
3. Azure App Configuration (when APP_CONFIG_ENDPOINT is set)
4. .env file (located in backend/.env)

Settings are organized into nested sub-settings classes with env-var prefixes:
- COSMOS_*              - Cosmos DB settings
- BLOBSTORAGE_*         - Blob Storage settings
- FOUNDRY_*             - Microsoft Foundry settings
- APPINSIGHTS_*         - Application Insights settings
- MCP_*                 - MCP client endpoint settings
- WORKFLOW_*            - Workflow execution settings
- API_*                 - API server settings
"""

from typing import Optional

from app.core.app_config_source import AppConfigAwareSettings
from app.models.config_options import (
    APIOptions,
    ApplicationInsightsOptions,
    BlobStorageOptions,
    CosmosDBOptions,
    FoundryOptions,
    KeyVaultOptions,
    MCPClientOptions,
    WorkflowOptions,
)
from pydantic import Field
from pydantic_settings import SettingsConfigDict


class CosmosDBSettings(AppConfigAwareSettings):
    """Azure Cosmos DB settings for workflow persistence."""

    model_config = SettingsConfigDict(env_prefix="COSMOS_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    endpoint: Optional[str] = Field(
        default=None, description="Cosmos DB endpoint URL (e.g., https://<account>.documents.azure.com:443/)"
    )
    connection_string: Optional[str] = Field(default=None, description="Connection string for dev/test only")
    database_name: str = Field(default="workflow-db", description="Database name")
    container_name: str = Field(default="workflows", description="Container name")
    partition_key_paths: list[str] = Field(
        default=["/user_id", "/serial_number"],
        description="Hierarchical Partition Key paths (HPK) for the container",
    )
    enable_ttl: bool = Field(default=True, description="Enable TTL on the container to auto-expire records")
    default_ttl_days: int = Field(default=30, description="Default TTL in days for workflow records")


class BlobStorageSettings(AppConfigAwareSettings):
    """Azure Blob Storage settings for artifact storage."""

    model_config = SettingsConfigDict(
        env_prefix="BLOBSTORAGE_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    account_url: Optional[str] = Field(
        default=None, description="Azure Storage Account URL (e.g., https://<account>.blob.core.windows.net/)"
    )
    connection_string: Optional[str] = Field(default=None, description="Connection string for dev/test only")
    artifacts_container: str = Field(default="artifacts", description="Artifacts container name")


class MicrosoftFoundrySettings(AppConfigAwareSettings):
    """Microsoft Foundry settings for agent orchestration."""

    model_config = SettingsConfigDict(env_prefix="FOUNDRY_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_endpoint: str = Field(default="", description="Microsoft Foundry project endpoint URL")
    image_processing_agent_id: str = Field(
        default="", description="Image processing agent ID (extracts serial numbers)"
    )
    reasoning_agent_id: str = Field(default="", description="Reasoning agent ID (generates recommendations)")
    image_processing_temperature: float = Field(default=0.1, description="Temperature for image processing agent")
    image_processing_max_tokens: int = Field(default=2048, description="Max tokens for image processing agent")
    reasoning_temperature: float = Field(default=0.3, description="Temperature for reasoning agent")
    reasoning_max_tokens: int = Field(default=4096, description="Max tokens for reasoning agent")


class ApplicationInsightsSettings(AppConfigAwareSettings):
    """Application Insights settings for telemetry."""

    model_config = SettingsConfigDict(
        env_prefix="APPINSIGHTS_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    connection_string: Optional[str] = Field(default=None, description="Application Insights connection string")
    enabled: bool = Field(default=True, description="Enable telemetry collection")
    sampling_percentage: float = Field(default=100.0, description="Telemetry sampling percentage")


class MCPClientSettings(AppConfigAwareSettings):
    """MCP client endpoint settings."""

    model_config = SettingsConfigDict(env_prefix="MCP_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    fsg_endpoint: str = Field(default="", description="FSG MCP endpoint URL")
    phoenix_endpoint: str = Field(default="", description="Phoenix MCP endpoint URL")
    timeout_seconds: int = Field(default=30, description="HTTP timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retries for failed requests")


class WorkflowSettings(AppConfigAwareSettings):
    """Workflow execution settings."""

    model_config = SettingsConfigDict(
        env_prefix="WORKFLOW_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class APISettings(AppConfigAwareSettings):
    """API server settings."""

    model_config = SettingsConfigDict(env_prefix="API_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")
    enable_cors: bool = Field(default=True, description="Enable CORS")
    enable_docs: bool = Field(default=True, description="Enable API documentation")


class KeyVaultSettings(AppConfigAwareSettings):
    """Azure Key Vault settings for secrets management."""

    model_config = SettingsConfigDict(
        env_prefix="KEYVAULT_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    url: Optional[str] = Field(
        default=None, description="Key Vault URL (e.g., https://<vault>.vault.azure.net/)"
    )
    use_key_vault: bool = Field(default=False, description="Enable Key Vault for secrets resolution")


class Settings(AppConfigAwareSettings):
    """Unified application settings loaded from environment variables or a ``.env`` file.

    Sub-settings classes are automatically populated from their prefixed env-vars
    when ``Settings`` is instantiated. Access typed options objects via the
    ``*_options`` properties which map nested settings to the ``BaseModel`` types
    consumed by the service layer.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application metadata
    app_name: str = Field(default="Workflow Automation API", description="Application name")
    environment: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Azure Identity (for service principal authentication in dev/test)
    azure_client_id: Optional[str] = Field(default=None, description="Azure AD client ID")
    azure_tenant_id: Optional[str] = Field(default=None, description="Azure AD tenant ID")
    azure_client_secret: Optional[str] = Field(default=None, description="Azure AD client secret")

    # Nested service settings
    cosmos_db: CosmosDBSettings = Field(default_factory=lambda: CosmosDBSettings())  # type: ignore[call-arg]
    blob_storage: BlobStorageSettings = Field(default_factory=lambda: BlobStorageSettings())  # type: ignore[call-arg]
    microsoft_foundry: MicrosoftFoundrySettings = Field(default_factory=lambda: MicrosoftFoundrySettings())  # type: ignore[call-arg]
    app_insights: ApplicationInsightsSettings = Field(default_factory=lambda: ApplicationInsightsSettings())  # type: ignore[call-arg]
    mcp_client: MCPClientSettings = Field(default_factory=lambda: MCPClientSettings())  # type: ignore[call-arg]
    workflow: WorkflowSettings = Field(default_factory=lambda: WorkflowSettings())  # type: ignore[call-arg]
    api: APISettings = Field(default_factory=lambda: APISettings())  # type: ignore[call-arg]
    key_vault: KeyVaultSettings = Field(default_factory=lambda: KeyVaultSettings())  # type: ignore[call-arg]

    # ──────────────────────────────────────────────────────────────────
    # Typed Options Properties
    # ──────────────────────────────────────────────────────────────────
    # These properties map from nested settings to config_options BaseModels

    @property
    def cosmos_db_options(self) -> CosmosDBOptions:
        """Create CosmosDBOptions from nested settings."""
        return CosmosDBOptions(
            endpoint=self.cosmos_db.endpoint,
            connection_string=self.cosmos_db.connection_string,
            database_name=self.cosmos_db.database_name,
            container_name=self.cosmos_db.container_name,
            partition_key_paths=self.cosmos_db.partition_key_paths,
            enable_ttl=self.cosmos_db.enable_ttl,
            default_ttl_days=self.cosmos_db.default_ttl_days,
        )

    @property
    def blob_storage_options(self) -> BlobStorageOptions:
        """Create BlobStorageOptions from nested settings."""
        return BlobStorageOptions(
            account_url=self.blob_storage.account_url,
            connection_string=self.blob_storage.connection_string,
            artifacts_container=self.blob_storage.artifacts_container,
        )

    @property
    def microsoft_foundry_options(self) -> FoundryOptions:
        """Create FoundryOptions from nested settings."""
        return FoundryOptions(
            project_endpoint=self.microsoft_foundry.project_endpoint,
            reasoning_agent_id=self.microsoft_foundry.reasoning_agent_id,
            image_processing_agent_id=self.microsoft_foundry.image_processing_agent_id,
            image_processing_temperature=self.microsoft_foundry.image_processing_temperature,
            image_processing_max_tokens=self.microsoft_foundry.image_processing_max_tokens,
            reasoning_temperature=self.microsoft_foundry.reasoning_temperature,
            reasoning_max_tokens=self.microsoft_foundry.reasoning_max_tokens,
        )

    @property
    def app_insights_options(self) -> ApplicationInsightsOptions:
        """Create ApplicationInsightsOptions from nested settings."""
        return ApplicationInsightsOptions(
            connection_string=self.app_insights.connection_string,
            enabled=self.app_insights.enabled,
            sampling_percentage=self.app_insights.sampling_percentage,
        )

    @property
    def mcp_client_options(self) -> MCPClientOptions:
        """Create MCPClientOptions from nested settings."""
        return MCPClientOptions(
            fsg_endpoint=self.mcp_client.fsg_endpoint,
            phoenix_endpoint=self.mcp_client.phoenix_endpoint,
            timeout_seconds=self.mcp_client.timeout_seconds,
            max_retries=self.mcp_client.max_retries,
        )

    @property
    def workflow_options(self) -> WorkflowOptions:
        """Create WorkflowOptions from nested settings."""
        return WorkflowOptions()

    @property
    def api_options(self) -> APIOptions:
        """Create APIOptions from nested settings."""
        return APIOptions(
            host=self.api.host, port=self.api.port, enable_cors=self.api.enable_cors, enable_docs=self.api.enable_docs
        )

    @property
    def key_vault_options(self) -> KeyVaultOptions:
        """Create KeyVaultOptions from nested settings."""
        return KeyVaultOptions(
            url=self.key_vault.url,
            use_key_vault=self.key_vault.use_key_vault,
        )

    # ──────────────────────────────────────────────────────────────────
    # Legacy property aliases for backward compatibility
    # ──────────────────────────────────────────────────────────────────
    # These allow existing code to continue using old attribute names

    @property
    def cosmos_endpoint(self) -> Optional[str]:
        """Legacy alias for cosmos_db.endpoint."""
        return self.cosmos_db.endpoint

    @property
    def cosmos_database(self) -> str:
        """Legacy alias for cosmos_db.database_name."""
        return self.cosmos_db.database_name

    @property
    def cosmos_container(self) -> str:
        """Legacy alias for cosmos_db.container_name."""
        return self.cosmos_db.container_name

    @property
    def blob_storage_account_url(self) -> Optional[str]:
        """Legacy alias for blob_storage.account_url."""
        return self.blob_storage.account_url

    @property
    def blob_artifacts_container(self) -> str:
        """Legacy alias for blob_storage.artifacts_container."""
        return self.blob_storage.artifacts_container

    @property
    def azure_ai_project_endpoint(self) -> str:
        """Legacy alias for microsoft_foundry.project_endpoint."""
        return self.microsoft_foundry.project_endpoint

    @property
    def foundry_reasoning_agent_id(self) -> str:
        """Legacy alias for microsoft_foundry.reasoning_agent_id."""
        return self.microsoft_foundry.reasoning_agent_id

    @property
    def applicationinsights_connection_string(self) -> Optional[str]:
        """Legacy alias for app_insights.connection_string."""
        return self.app_insights.connection_string

    @property
    def fsg_endpoint(self) -> str:
        """Legacy alias for mcp_client.fsg_endpoint."""
        return self.mcp_client.fsg_endpoint

    @property
    def phoenix_endpoint(self) -> str:
        """Legacy alias for mcp_client.phoenix_endpoint."""
        return self.mcp_client.phoenix_endpoint


# ──────────────────────────────────────────────────────────────────────
# Singleton instance
# ──────────────────────────────────────────────────────────────────────

_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Return the module-level ``Settings`` singleton, creating it on first call.

    Returns:
        The shared ``Settings`` instance populated from env-vars / ``.env``.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
