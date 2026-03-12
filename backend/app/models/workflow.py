"""Domain models for serial number workflow and execution state.

This module contains all Pydantic models related to serial number processing workflow,
including workflow state, execution tracking, and Cosmos DB persistence.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """Status of workflow execution.

    Tracks the lifecycle of a workflow from initial request through completion or failure.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SerialNumberData(BaseModel):
    """Extracted serial number information from image processing.

    Attributes:
        serial_number: The primary serial number extracted from the image.
        model_number: Associated model or part number if available.
        additional_identifiers: Any other identifiers found (MAC address, UUID, etc.).
        location: Where on the device/label the serial number was found.
        condition: Physical condition of the label (clear, worn, damaged).
        confidence: Confidence score from 0.0 to 1.0 from the vision model.
        notes: Additional observations from the image analysis.
    """

    serial_number: Optional[str] = Field(default=None, description="Primary serial number extracted")
    model_number: Optional[str] = Field(default=None, description="Associated model or part number")
    additional_identifiers: Dict[str, str] = Field(
        default_factory=dict, description="Additional identifiers (MAC, UUID, etc.)"
    )
    location: Optional[str] = Field(default=None, description="Location of serial number on device")
    condition: Optional[str] = Field(default=None, description="Physical condition of label")
    confidence: Optional[float] = Field(default=None, description="Confidence score (0.0-1.0)")
    notes: Optional[str] = Field(default=None, description="Additional observations")


class FSGLookupResult(BaseModel):
    """Result from FSG (Field Service Guide) system lookup.

    Contains warranty, coverage, and service information for the device.
    """

    warranty_status: Optional[str] = Field(default=None, description="Current warranty status")
    coverage_end_date: Optional[str] = Field(default=None, description="Warranty coverage end date")
    service_level: Optional[str] = Field(default=None, description="Service level or tier")
    product_line: Optional[str] = Field(default=None, description="Product line classification")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional FSG metadata")


class PhoenixEnrichmentResult(BaseModel):
    """Result from Phoenix system enrichment.

    Contains additional contextual data and recommendations.
    """

    enrichment_data: Dict[str, Any] = Field(default_factory=dict, description="Enriched contextual data")
    recommendations: List[str] = Field(default_factory=list, description="System recommendations")
    risk_indicators: List[str] = Field(default_factory=list, description="Identified risk factors")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional Phoenix metadata")


class ReasoningOutput(BaseModel):
    """Output from reasoning.

    Contains the final analysis, recommendations, and decision from the reasoning step.
    """

    analysis: str = Field(..., description="Detailed analysis of all gathered information")
    recommendations: List[str] = Field(default_factory=list, description="Action recommendations")
    confidence: Optional[float] = Field(default=None, description="Overall confidence score (0.0-1.0)")
    next_steps: List[str] = Field(default_factory=list, description="Suggested next steps")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional reasoning metadata")


class WorkflowState(BaseModel):
    """State object passed between workflow executors.

    Tracks the complete workflow execution through all stages:
    1. Image processing / serial number extraction
    2. FSG system lookup
    3. Phoenix system enrichment
    4. Reasoning
    5. Cosmos DB persistence

    The thought_process field captures each step with detailed metadata for observability
    and debugging. Each executor appends its execution details to this list.

    Attributes:
        serial_number: The primary serial number being processed.
        text: Optional text input provided with the request.
        image_bytes: Raw image bytes if an image was provided.
        current_step: Current executor step in the workflow.
        max_retries: Maximum retry attempts for failed steps.
        current_retry: Current retry attempt counter.
        artifact_url: URL where uploaded image artifact is stored (Blob Storage).
        serial_data: Extracted serial number information.
        fsg_data: FSG system lookup results.
        phoenix_data: Phoenix enrichment results.
        reasoning: Reasoning output.
        error: Error message if workflow failed.
        thought_process: Detailed step-by-step execution log for observability.
    """

    serial_number: str = Field(..., description="Primary serial number being processed")
    text: Optional[str] = Field(default=None, description="Optional text input from request")
    image_bytes: Optional[bytes] = Field(default=None, description="Raw image bytes if provided")

    # Execution control
    current_step: Literal[
        "artifact_storage",
        "image_processing",
        "fsg_lookup",
        "phoenix_enrichment",
        "reasoning_agent",
        "cosmos_persistence",
    ] = Field(default="artifact_storage", description="Current workflow step")
    max_retries: int = Field(default=3, description="Maximum retry attempts per step")
    current_retry: int = Field(default=0, description="Current retry attempt")

    # Step outputs
    artifact_url: Optional[str] = Field(default=None, description="Blob Storage URL for uploaded image")
    serial_data: Optional[SerialNumberData] = Field(default=None, description="Extracted serial number data")
    fsg_data: Optional[FSGLookupResult] = Field(default=None, description="FSG system lookup results")
    phoenix_data: Optional[PhoenixEnrichmentResult] = Field(default=None, description="Phoenix enrichment results")
    reasoning: Optional[ReasoningOutput] = Field(default=None, description="Foundry reasoning output")

    # Error tracking
    error: Optional[str] = Field(default=None, description="Error message if workflow failed")

    # Observability - detailed execution log
    # Each entry has {"step": str, "details": dict, "timestamp": str, "success": bool}
    # Example: {"step": "fsg_lookup", "details": {...}, "timestamp": "2026-03-11T10:30:00Z", "success": true}
    thought_process: List[Dict[str, Any]] = Field(
        default_factory=list, description="Step-by-step execution log with metadata"
    )


class WorkflowRecord(BaseModel):
    """Cosmos DB workflow persistence record.

    Represents a complete workflow execution stored in Cosmos DB.
    Uses serial_number as the partition key for efficient lookup by serial number.

    Attributes:
        id: Unique item ID in format {serial_number}_{timestamp}
        serial_number: Serial number (partition key)
        status: Current workflow status
        input_data: Original request input data
        result_data: Final workflow results and outputs
        error_message: Error details if workflow failed
        created_at: Workflow creation timestamp in UTC
        updated_at: Last update timestamp in UTC
        completed_at: Completion timestamp in UTC (if completed)
        thought_process: Execution log copied from WorkflowState
    """

    id: str = Field(..., description="Unique item ID")
    serial_number: str = Field(..., description="Serial number (partition key)")
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING, description="Workflow status")

    # Input and output data
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Original request inputs")
    result_data: Dict[str, Any] = Field(default_factory=dict, description="Final workflow results")
    error_message: Optional[str] = Field(default=None, description="Error details if failed")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Workflow creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp"
    )
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")

    # Observability
    thought_process: List[Dict[str, Any]] = Field(default_factory=list, description="Execution log from WorkflowState")
