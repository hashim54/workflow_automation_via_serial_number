"""Configuration status endpoint for debugging."""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_workflow_service
from app.services.workflow_service import WorkflowService
from app.core.config_validator import ConfigValidator

router = APIRouter()


@router.get("/config-status")
async def get_config_status(
    service: WorkflowService = Depends(get_workflow_service),
) -> dict:
    """
    Get configuration status for all services.
    
    Useful for debugging - shows which services are configured and which are missing.
    """
    validator = ConfigValidator(service._settings)
    validator.validate_all()
    
    return {
        "status": "configured" if validator.validate_all() else "incomplete",
        "details": validator.get_issues_summary(),
        "components": {
            "cosmos_db": validator.is_component_configured("CosmosDB"),
            "blob_storage": validator.is_component_configured("BlobStorage"),
            "microsoft_foundry": validator.is_component_configured("MicrosoftFoundry"),
            "mcp_client": validator.is_component_configured("MCPClient"),
            "application_insights": validator.is_component_configured("ApplicationInsights"),
        },
    }
