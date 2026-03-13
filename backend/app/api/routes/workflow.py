from app.api.dependencies import get_workflow_service
from app.api.schemas.workflow import WorkflowRequest, WorkflowResponse
from app.services.workflow_service import WorkflowService
from fastapi import APIRouter, Depends, HTTPException, UploadFile

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
) -> WorkflowResponse:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported file type '{file.content_type}'. " f"Allowed: {', '.join(sorted(ALLOWED_IMAGE_TYPES))}"
            ),
        )

    data = await file.read(1)
    if not data:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    # Read the rest in chunks, rejecting as soon as the size limit is exceeded
    # to avoid buffering the full payload unnecessarily.
    _CHUNK = 64 * 1024  # 64 KB
    chunks = [data]
    total = len(data)
    while True:
        chunk = await file.read(_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(
                status_code=422,
                detail=f"File too large. Maximum allowed: {MAX_IMAGE_SIZE_BYTES} bytes (10 MB).",
            )
        chunks.append(chunk)
    data = b"".join(chunks)

    request = WorkflowRequest(image_bytes=data, content_type=file.content_type)
    return await service.execute(request)


@router.get("/{serial_number}", response_model=WorkflowResponse)
async def get_workflow_status(
    serial_number: str,
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowResponse:
    return await service.get_status(serial_number)
