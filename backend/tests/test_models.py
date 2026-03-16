"""Unit tests for workflow models."""

from datetime import datetime

import pytest
from app.models.workflow import (
    ComplianceData,
    ElectricalData,
    ExtractionContext,
    FSGLookupResult,
    IdentificationData,
    MechanicalData,
    PhoenixEnrichmentResult,
    ReasoningOutput,
    SerialNumberData,
    ThermalProtectionData,
    WorkflowRecord,
    WorkflowState,
    WorkflowStatus,
)
from pydantic import ValidationError


@pytest.mark.unit
class TestWorkflowState:
    """Test WorkflowState model."""

    def test_create_basic_state(self):
        """Test creating a basic workflow state."""
        state = WorkflowState(serial_number="SN-12345")

        assert state.serial_number == "SN-12345"
        assert state.current_step == "artifact_storage"
        assert state.artifact_url is None
        assert state.serial_data is None
        assert state.fsg_data is None
        assert state.phoenix_data is None
        assert state.reasoning is None
        assert state.error is None
        assert state.thought_process == []

    def test_state_with_all_fields(self):
        """Test workflow state with all fields populated."""
        serial_data = SerialNumberData(
            identification=IdentificationData(
                serial_number_raw="SN-67890",
                normalized_serial_number="67890",
            ),
            context=ExtractionContext(confidence="high"),
        )
        fsg_data = FSGLookupResult(warranty_status="active", service_level="premium")
        phoenix_data = PhoenixEnrichmentResult(enrichment_data={"key": "value"})
        reasoning = ReasoningOutput(analysis="Test analysis", recommendations=["action1"])

        state = WorkflowState(
            serial_number="SN-67890",
            current_step="reasoning_agent",
            artifact_url="https://storage.blob.core.windows.net/artifacts/SN-67890.json",
            serial_data=serial_data,
            fsg_data=fsg_data,
            phoenix_data=phoenix_data,
            reasoning=reasoning,
        )

        assert state.current_step == "reasoning_agent"
        assert state.artifact_url is not None
        assert state.serial_data is not None
        assert state.serial_data.serial_number == "SN-67890"
        assert state.serial_data.normalized_serial_number == "67890"
        assert state.fsg_data is not None
        assert state.phoenix_data is not None
        assert state.reasoning is not None

    def test_state_with_error(self):
        """Test workflow state with error."""
        state = WorkflowState(
            serial_number="SN-ERROR",
            error="Connection timeout",
        )

        assert state.error == "Connection timeout"

    def test_step_literals(self):
        """Test that only valid step values are accepted."""
        valid_steps = [
            "artifact_storage",
            "image_processing",
            "fsg_lookup",
            "phoenix_enrichment",
            "reasoning_agent",
            "cosmos_persistence",
        ]

        for step in valid_steps:
            state = WorkflowState(serial_number="SN-TEST", current_step=step)  # type: ignore[arg-type]
            assert state.current_step == step

    def test_invalid_step_raises_error(self):
        """Test that invalid step values raise ValidationError."""
        with pytest.raises(ValidationError):
            WorkflowState(serial_number="SN-TEST", current_step="invalid_step")  # type: ignore[arg-type]

    def test_thought_process_tracking(self):
        """Test thought process logging."""
        state = WorkflowState(serial_number="SN-TRACK")

        # Add thought process entries
        state.thought_process.append(
            {
                "step": "artifact_storage",
                "details": {"url": "https://..."},
                "timestamp": "2026-03-11T10:00:00Z",
                "success": True,
            }
        )

        assert len(state.thought_process) == 1
        assert state.thought_process[0]["step"] == "artifact_storage"
        assert state.thought_process[0]["success"] is True


@pytest.mark.unit
class TestWorkflowRecord:
    """Test WorkflowRecord model for Cosmos DB."""

    def test_create_record(self):
        """Test creating a workflow record."""
        record = WorkflowRecord(id="SN-12345_2026-03-11T10:00:00", serial_number="SN-12345")

        assert record.id == "SN-12345_2026-03-11T10:00:00"
        assert record.serial_number == "SN-12345"
        assert record.status == WorkflowStatus.PENDING
        assert isinstance(record.created_at, datetime)
        assert isinstance(record.updated_at, datetime)

    def test_record_with_results(self):
        """Test record with workflow results."""
        record = WorkflowRecord(
            id="SN-COMPLETE_2026-03-11T10:00:00",
            serial_number="SN-COMPLETE",
            status=WorkflowStatus.COMPLETED,
            input_data={"serial_number": "SN-COMPLETE", "text": "test"},
            result_data={"recommendation": "replace", "confidence": 0.9},
            completed_at=datetime.now(),
        )

        assert record.status == WorkflowStatus.COMPLETED
        assert record.input_data["serial_number"] == "SN-COMPLETE"
        assert record.result_data["recommendation"] == "replace"
        assert record.completed_at is not None

    def test_timestamps_auto_set(self):
        """Test that timestamps are automatically set."""
        record = WorkflowRecord(id="SN-TIME_2026-03-11T10:00:00", serial_number="SN-TIME")

        assert record.created_at is not None
        assert record.updated_at is not None

    def test_partition_key_matches_serial_number(self):
        """Test that partition key matches serial number."""
        record = WorkflowRecord(id="SN-PARTITION_2026-03-11T10:00:00", serial_number="SN-PARTITION")

        assert record.serial_number == "SN-PARTITION"
        # In Cosmos DB, serial_number is the partition key


@pytest.mark.unit
class TestSerialNumberData:
    """Test SerialNumberData model."""

    def test_create_minimal(self):
        """Test creating with minimal data."""
        data = SerialNumberData()

        assert data.serial_number is None
        assert data.confidence is None
        assert data.additional_identifiers == {}

    def test_create_complete(self):
        """Test creating with complete data."""
        data = SerialNumberData(
            serial_number="SN-TEST-001",
            model_number="MODEL-X",
            additional_identifiers={"MAC": "00:11:22:33:44:55"},
            location="bottom panel",
            condition="clear",
            confidence=0.98,
            notes="Label is in excellent condition",
        )

        assert data.serial_number == "SN-TEST-001"
        assert data.confidence == 0.98
        assert "MAC" in data.additional_identifiers


@pytest.mark.unit
class TestReasoningOutput:
    """Test ReasoningOutput model."""

    def test_create_reasoning(self):
        """Test creating reasoning output."""
        reasoning = ReasoningOutput(
            analysis="Device shows signs of wear",
            recommendations=["Replace part A", "Check connection B"],
            confidence=0.85,
            next_steps=["Order replacement", "Schedule maintenance"],
        )

        assert reasoning.analysis == "Device shows signs of wear"
        assert len(reasoning.recommendations) == 2
        assert reasoning.confidence == 0.85
        assert len(reasoning.next_steps) == 2
