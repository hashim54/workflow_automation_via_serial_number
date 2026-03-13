import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.api.dependencies import get_blob_storage_service, get_foundry_service, get_settings, get_workflow_service
from app.api.schemas.workflow import WorkflowRequest, WorkflowResponse
from app.core.settings import Settings
from app.services.blob_storage_service import BlobStorageService
from app.services.foundry_service import FoundryService
from app.services.workflow_service import WorkflowService

router = APIRouter()

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/tiff",
}

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/", response_model=WorkflowResponse)
async def trigger_workflow(
    file: UploadFile,
    service: WorkflowService = Depends(get_workflow_service),
    blob_storage: BlobStorageService = Depends(get_blob_storage_service),
    foundry: FoundryService = Depends(get_foundry_service),
    settings: Settings = Depends(get_settings),
) -> WorkflowResponse:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_IMAGE_TYPES))}"
            ),
        )

    data = await file.read()

    if len(data) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    if len(data) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=422,
            detail=f"File too large ({len(data)} bytes). Maximum allowed: {MAX_IMAGE_SIZE_BYTES} bytes (10 MB).",
        )

    # Upload image to Blob Storage
    image_url = await blob_storage.upload_artifact(
        container=settings.blob_artifacts_container,
        blob_name=file.filename,
        data=data,
    )

    # Send image to Foundry Image Processing Agent for extraction
    extraction_result = await foundry.extract_from_image(
        image_bytes=data,
        content_type=file.content_type,
    )

    request = WorkflowRequest(image_url=image_url, extraction_result=extraction_result)
    return await service.execute(request)


@router.get("/{serial_number}", response_model=WorkflowResponse)
async def get_workflow_status(
    serial_number: str,
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowResponse:
    return await service.get_status(serial_number)
