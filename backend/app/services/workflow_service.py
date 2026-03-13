"""Workflow service for orchestrating serial number workflow execution."""

from typing import Optional

from fastapi import HTTPException

from app.api.schemas.workflow import WorkflowRequest, WorkflowResponse
from app.core.settings import Settings
from app.core.config_validator import ConfigValidator
from app.workflows.core import SerialNumberWorkflow


class WorkflowService:
    """
    High-level service for workflow execution and status retrieval.
    
    This service validates configuration before attempting workflow execution
    and provides helpful error messages when services are not configured.
    """

    def __init__(self, settings: Settings, workflow: Optional[SerialNumberWorkflow] = None) -> None:
        self._settings = settings
        self._workflow = workflow
        self._validator = ConfigValidator(settings)

    def _check_configuration(self) -> None:
        """
        Validate that all required services are configured.
        
        Raises:
            HTTPException: If configuration is incomplete.
        """
        if not self._validator.validate_all():
            summary = self._validator.get_issues_summary()
            
            error_details = {
                "error": "Configuration incomplete",
                "message": "Workflow cannot execute - required services are not configured",
                "missing_configuration": summary["errors"],
            }
            
            if summary["warnings"]:
                error_details["warnings"] = summary["warnings"]
            
            raise HTTPException(
                status_code=503,
                detail=error_details,
            )

    async def execute(self, request: WorkflowRequest) -> WorkflowResponse:
        """
        Execute workflow for a serial number.
        
        Args:
            request: Workflow execution request
        
        Returns:
            WorkflowResponse with execution results
        
        Raises:
            HTTPException: If configuration is incomplete or execution fails
        """
        # Validate configuration before attempting execution
        self._check_configuration()
        
        # TODO: Implement workflow execution
        # result = await self._workflow.execute(
        #     serial_number=request.serial_number,
        #     data=request.data
        # )
        
        # For now, return a placeholder response
        return WorkflowResponse(
            status="not_implemented",
            image_url=request.image_url,
            result={
                "message": "Workflow execution not yet implemented",
                "configuration_valid": True,
            },
        )

    async def get_status(self, serial_number: str) -> WorkflowResponse:
        """
        Get workflow status for a serial number.
        
        Args:
            serial_number: Serial number to look up
        
        Returns:
            WorkflowResponse with current status
        
        Raises:
            HTTPException: If configuration is incomplete or lookup fails
        """
        # Check if Cosmos DB is configured (needed for status lookup)
        if not self._validator.is_component_configured("CosmosDB"):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Cosmos DB not configured",
                    "message": "Cannot retrieve workflow status - database not configured",
                    "component": "CosmosDB",
                },
            )
        
        # TODO: Implement status lookup from Cosmos DB
        # state = await self._cosmos.get_workflow_state(serial_number)
        
        # For now, return a placeholder response
        return WorkflowResponse(
            status="not_found",
            result={
                "message": "Status lookup not yet implemented",
            },
        )
