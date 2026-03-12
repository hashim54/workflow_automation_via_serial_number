"""
Serial Number Workflow — core orchestration.

Defines SerialNumberWorkflow, which inherits the five executor steps from
SerialNumberWorkflowExecutors (executors.py) and adds the build_workflow()
entry point that wires everything together via the Microsoft Agent Framework
WorkflowBuilder.

Flow (deterministic, no branching):
    Artifact Storage → FSG Lookup → Phoenix Enrichment → Foundry Reasoning → Cosmos Persistence → Complete

This is a linear pipeline with no conditional routing — each step feeds directly
into the next.
"""

from agent_framework import WorkflowBuilder, Workflow
from agent_framework._workflows._function_executor import FunctionExecutor

from app.workflows.executors import SerialNumberWorkflowExecutors


class SerialNumberWorkflow(SerialNumberWorkflowExecutors):
    """
    Serial Number Workflow orchestrating deterministic data collection and AI reasoning.

    Inherits the executor steps from SerialNumberWorkflowExecutors and adds:
    - build_workflow() to assemble and return the runnable Workflow

    See SerialNumberWorkflowExecutors for constructor parameters.
    """

    # ------------------------------------------------------------------
    # Workflow construction
    # ------------------------------------------------------------------

    def build_workflow(self) -> Workflow:
        """
        Build and return the configured workflow.

        Creates a linear execution pipeline with the following steps:
        1. Artifact Storage
        2. FSG Lookup (MCP)
        3. Phoenix Enrichment (MCP)
        4. Foundry Reasoning
        5. Cosmos Persistence

        Returns:
            Configured workflow with sequential execution
        """
        self.logger.info("Building Serial Number Workflow...")

        # Create function executors from instance methods
        artifact_storage_exec = FunctionExecutor(
            self.artifact_storage_executor, id="artifact_storage"
        )
        fsg_lookup_exec = FunctionExecutor(self.fsg_lookup_executor, id="fsg_lookup")
        phoenix_enrichment_exec = FunctionExecutor(
            self.phoenix_enrichment_executor, id="phoenix_enrichment"
        )
        reasoning_exec = FunctionExecutor(
            self.reasoning_executor, id="reasoning_agent"
        )
        cosmos_persistence_exec = FunctionExecutor(
            self.cosmos_persistence_executor, id="cosmos_persistence"
        )

        # Build workflow with linear execution
        workflow = (
            WorkflowBuilder()
            .set_start_executor(artifact_storage_exec)
            .add_edge(artifact_storage_exec, fsg_lookup_exec)
            .add_edge(fsg_lookup_exec, phoenix_enrichment_exec)
            .add_edge(phoenix_enrichment_exec, reasoning_exec)
            .add_edge(reasoning_exec, cosmos_persistence_exec)
            .build()
        )

        self.logger.info(
            "Serial Number workflow built: "
            "artifact_storage → fsg_lookup → phoenix_enrichment → "
            "reasoning_agent → cosmos_persistence"
        )
        return workflow
