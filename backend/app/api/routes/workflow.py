from fastapi import APIRouter, Depends

from app.api.dependencies import get_workflow_service
from app.api.schemas.workflow import WorkflowRequest, WorkflowResponse
from app.services.workflow_service import WorkflowService

router = APIRouter()


@router.post("/", response_model=WorkflowResponse)
async def trigger_workflow(
    request: WorkflowRequest,
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowResponse:
    return await service.execute(request)


@router.get("/{serial_number}", response_model=WorkflowResponse)
async def get_workflow_status(
    serial_number: str,
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowResponse:
    return await service.get_status(serial_number)
