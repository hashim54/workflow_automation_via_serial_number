from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from app.core.container import Container
from app.core.settings import Settings
from app.services.blob_storage_service import BlobStorageService
from app.services.foundry_service import FoundryService
from app.services.workflow_service import WorkflowService


@inject
def get_workflow_service(
    service: WorkflowService = Depends(Provide[Container.workflow_service]),
) -> WorkflowService:
    return service


@inject
def get_blob_storage_service(
    service: BlobStorageService = Depends(Provide[Container.blob_storage]),
) -> BlobStorageService:
    return service


@inject
def get_foundry_service(
    service: FoundryService = Depends(Provide[Container.foundry]),
) -> FoundryService:
    return service


@inject
def get_settings(
    settings: Settings = Depends(Provide[Container.settings]),
) -> Settings:
    return settings
