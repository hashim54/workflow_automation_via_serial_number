"""Configuration validation utilities."""

from dataclasses import dataclass
from typing import Any, Dict, List

from app.core.settings import Settings


@dataclass
class ValidationIssue:
    """Represents a configuration validation issue."""

    component: str
    field: str
    message: str
    severity: str = "error"  # "error" or "warning"


class ConfigValidator:
    """Validates application configuration for required services."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.issues: List[ValidationIssue] = []

    def validate_all(self) -> bool:
        """
        Validate all configuration requirements.

        Returns:
            True if all required config is present, False otherwise.
        """
        self.issues = []

        self.validate_cosmos_db()
        self.validate_blob_storage()
        self.validate_foundry()
        self.validate_mcp_clients()
        self.validate_app_insights()

        # Return True only if no errors (warnings are OK)
        return not any(issue.severity == "error" for issue in self.issues)

    def validate_cosmos_db(self) -> bool:
        """Validate Cosmos DB configuration."""
        cosmos = self.settings.cosmos_db

        if not cosmos.endpoint and not cosmos.connection_string:
            self.issues.append(
                ValidationIssue(
                    component="CosmosDB",
                    field="endpoint/connection_string",
                    message="Either endpoint or connection_string must be provided",
                    severity="error",
                )
            )
            return False

        if not cosmos.database_name:
            self.issues.append(
                ValidationIssue(
                    component="CosmosDB", field="database_name", message="Database name is required", severity="error"
                )
            )
            return False

        if not cosmos.container_name:
            self.issues.append(
                ValidationIssue(
                    component="CosmosDB", field="container_name", message="Container name is required", severity="error"
                )
            )
            return False

        return True

    def validate_blob_storage(self) -> bool:
        """Validate Blob Storage configuration."""
        blob = self.settings.blob_storage

        if not blob.account_url and not blob.connection_string:
            self.issues.append(
                ValidationIssue(
                    component="BlobStorage",
                    field="account_url/connection_string",
                    message="Either account_url or connection_string must be provided",
                    severity="error",
                )
            )
            return False

        if not blob.artifacts_container:
            self.issues.append(
                ValidationIssue(
                    component="BlobStorage",
                    field="artifacts_container",
                    message="Artifacts container name is required",
                    severity="error",
                )
            )
            return False

        return True

    def validate_foundry(self) -> bool:
        """Validate Microsoft Foundry configuration."""
        foundry = self.settings.microsoft_foundry

        if not foundry.project_endpoint:
            self.issues.append(
                ValidationIssue(
                    component="MicrosoftFoundry",
                    field="project_endpoint",
                    message="Project endpoint is required",
                    severity="error",
                )
            )
            return False

        if not foundry.image_processing_agent_id:
            self.issues.append(
                ValidationIssue(
                    component="MicrosoftFoundry",
                    field="image_processing_agent_id",
                    message="Image processing agent ID is required",
                    severity="error",
                )
            )
            return False

        if not foundry.reasoning_agent_id:
            self.issues.append(
                ValidationIssue(
                    component="MicrosoftFoundry",
                    field="reasoning_agent_id",
                    message="Reasoning agent ID is required",
                    severity="error",
                )
            )
            return False

        return True

    def validate_mcp_clients(self) -> bool:
        """Validate MCP client configuration (optional)."""
        mcp = self.settings.mcp_client

        if not mcp.fsg_endpoint:
            self.issues.append(
                ValidationIssue(
                    component="MCPClient",
                    field="fsg_endpoint",
                    message="FSG endpoint not configured - FSG lookups will be unavailable",
                    severity="warning",
                )
            )

        if not mcp.phoenix_endpoint:
            self.issues.append(
                ValidationIssue(
                    component="MCPClient",
                    field="phoenix_endpoint",
                    message="Phoenix endpoint not configured - Phoenix enrichment will be unavailable",
                    severity="warning",
                )
            )

        return True

    def validate_app_insights(self) -> bool:
        """Validate Application Insights configuration (optional)."""
        app_insights = self.settings.app_insights

        if app_insights.enabled and not app_insights.connection_string:
            self.issues.append(
                ValidationIssue(
                    component="ApplicationInsights",
                    field="connection_string",
                    message="Connection string required when telemetry is enabled",
                    severity="warning",  # Just a warning, not critical
                )
            )
            return False

        return True

    def get_issues_summary(self) -> Dict[str, Any]:
        """Get a summary of validation issues."""
        errors = [i for i in self.issues if i.severity == "error"]
        warnings = [i for i in self.issues if i.severity == "warning"]

        return {
            "valid": len(errors) == 0,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": [
                {
                    "component": i.component,
                    "field": i.field,
                    "message": i.message,
                }
                for i in errors
            ],
            "warnings": [
                {
                    "component": i.component,
                    "field": i.field,
                    "message": i.message,
                }
                for i in warnings
            ],
        }

    def is_component_configured(self, component: str) -> bool:
        """
        Check if a specific component is configured.

        Args:
            component: Component name (CosmosDB, BlobStorage, MicrosoftFoundry, MCPClient)

        Returns:
            True if component is fully configured.
        """
        validators = {
            "CosmosDB": self.validate_cosmos_db,
            "BlobStorage": self.validate_blob_storage,
            "MicrosoftFoundry": self.validate_foundry,
            "MCPClient": self.validate_mcp_clients,
            "ApplicationInsights": self.validate_app_insights,
        }

        if component not in validators:
            return False

        # Clear existing issues for this component
        self.issues = [i for i in self.issues if i.component != component]

        return validators[component]()
