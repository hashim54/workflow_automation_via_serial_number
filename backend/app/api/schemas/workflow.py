from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class WorkflowRequest(BaseModel):
    image_url: Optional[str] = Field(default=None, description="Blob Storage URL of the uploaded image")
    extraction_result: Dict[str, Any] = Field(default_factory=dict, description="Extracted data from the image")
    data: dict = {}


class WorkflowResponse(BaseModel):
    status: str
    image_url: Optional[str] = Field(default=None, description="Blob Storage URL of the uploaded image")
    extraction_result: Dict[str, Any] = Field(default_factory=dict, description="Extracted data from the image")
    result: dict = {}
