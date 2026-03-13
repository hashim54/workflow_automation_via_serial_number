from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class WorkflowRequest(BaseModel):
    image_bytes: bytes = Field(..., description="Raw image bytes uploaded by the client")
    content_type: str = Field(..., description="MIME type of the uploaded image (e.g. image/jpeg)")


class WorkflowResponse(BaseModel):
    status: str
    image_url: Optional[str] = Field(default=None, description="Blob Storage URL of the uploaded image")
    extraction_result: Dict[str, Any] = Field(default_factory=dict, description="Extracted data from the image")
    result: dict = {}
