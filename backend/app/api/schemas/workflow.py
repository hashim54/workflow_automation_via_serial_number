from typing import Optional

from pydantic import BaseModel, Field


class WorkflowRequest(BaseModel):
    image_url: Optional[str] = Field(default=None, description="Blob Storage URL of the uploaded image")
    data: dict = {}


class WorkflowResponse(BaseModel):
    status: str
    image_url: Optional[str] = Field(default=None, description="Blob Storage URL of the uploaded image")
    result: dict = {}
