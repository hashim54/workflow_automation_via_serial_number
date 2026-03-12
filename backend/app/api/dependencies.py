from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from app.core.container import Container
from app.services.workflow_service import WorkflowService


@inject
def get_workflow_service(
    service: WorkflowService = Depends(Provide[Container.workflow_service]),
) -> WorkflowService:
    return service
