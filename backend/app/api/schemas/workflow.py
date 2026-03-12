from pydantic import BaseModel, Field


class WorkflowRequest(BaseModel):
    serial_number: str = Field(..., min_length=1, description="Serial number to process")
    data: dict = {}


class WorkflowResponse(BaseModel):
    serial_number: str
    status: str
    result: dict = {}
