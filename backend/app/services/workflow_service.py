"""Workflow service for orchestrating serial number workflow execution."""

from typing import Optional

from agent_framework import WorkflowRunState
from app.api.schemas.workflow import WorkflowRequest, WorkflowResponse
from app.core.config_validator import ConfigValidator
from app.core.settings import Settings
from app.models.workflow import WorkflowState
from app.workflows.core import SerialNumberWorkflow
from fastapi import HTTPException


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

        if self._workflow is None:
            raise HTTPException(status_code=503, detail="Workflow is not configured.")

        initial_state = WorkflowState(
            image_bytes=request.image_bytes,
            content_type=request.content_type,
        )

        workflow = self._workflow.build_workflow()
        run_result = await workflow.run(initial_state)

        final_run_state = run_result.get_final_state()
        outputs = run_result.get_outputs()
        final_state: WorkflowState = outputs[-1] if outputs else initial_state

        if final_run_state == WorkflowRunState.FAILED or final_state.error:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Workflow execution failed",
                    "message": final_state.error or "Unknown error",
                },
            )

        return WorkflowResponse(
            status="completed",
            image_url=final_state.artifact_url,
            extraction_result=final_state.serial_data.model_dump() if final_state.serial_data else {},
            result=final_state.reasoning.model_dump() if final_state.reasoning else {},
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
