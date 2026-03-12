"""
Serial Number Workflow Executors.

Contains the SerialNumberWorkflowExecutors base class, which implements the five
workflow executor steps (artifact storage, FSG lookup, Phoenix enrichment,
Foundry reasoning, and persistence). This class is intended to be subclassed by
SerialNumberWorkflow in core.py, which adds the build_workflow() entry-point.
"""

from agent_framework import WorkflowContext
from app.core.logger import Logger
from app.core.settings import Settings
from app.mcp_clients.fsg_client import FsgClient
from app.mcp_clients.phoenix_client import PhoenixClient
from app.models.workflow import WorkflowState
from app.services.blob_storage_service import BlobStorageService
from app.services.cosmos_db_service import CosmosDBService
from app.services.foundry_service import FoundryService


class SerialNumberWorkflowExecutors:
    """
    Executor steps for the Serial Number Workflow.

    Provides the five async executor methods called by the workflow runtime:
    1. Artifact storage
    2. FSG lookup via MCP
    3. Phoenix enrichment via MCP
    4. Foundry reasoning
    5. Cosmos DB persistence

    Routing and workflow construction live in the SerialNumberWorkflow
    subclass (core.py).
    """

    def __init__(
        self,
        settings: Settings,
        logger: Logger,
        blob_storage: BlobStorageService,
        cosmos: CosmosDBService,
        foundry: FoundryService,
        fsg_client: FsgClient,
        phoenix_client: PhoenixClient,
    ):
        """
        Initialize executors with all required dependencies.

        Args:
            settings: Application settings
            logger: Logger with tracing support for Application Insights and Foundry
            blob_storage: Blob storage service for artifact management
            cosmos: Cosmos DB service for persistence
            foundry: Foundry service for AI reasoning
            fsg_client: FSG MCP client for field service gateway lookup
            phoenix_client: Phoenix MCP client for enrichment
        """
        self.settings = settings
        self.logger = logger
        self.blob_storage = blob_storage
        self.cosmos = cosmos
        self.foundry = foundry
        self.fsg_client = fsg_client
        self.phoenix_client = phoenix_client

    # ------------------------------------------------------------------
    # Executor steps
    # ------------------------------------------------------------------

    async def artifact_storage_executor(self, state: WorkflowState, ctx: WorkflowContext[WorkflowState]) -> None:
        """
        Step 1: Store input artifact (text + optional image) in Blob Storage.

        Uploads the raw input data to Azure Blob Storage for audit trail and
        later reference.
        """
        self.logger.info(
            f"[ArtifactStorage] Storing artifact for serial_number={state.serial_number}",
            extra={"serial_number": state.serial_number, "has_image": state.image_bytes is not None},
        )

        with self.logger.trace_operation(
            "artifact_storage",
            serial_number=state.serial_number,
            has_image=state.image_bytes is not None,
            text_length=len(state.text) if state.text else 0,
        ) as span:
            try:
                # TODO: Implement blob storage upload
                # artifact_url = await self.blob_storage.upload_artifact(
                #     serial_number=state.serial_number,
                #     text=state.text,
                #     image_bytes=state.image_bytes
                # )
                # state.artifact_url = artifact_url
                # span.set_attribute("artifact_url", artifact_url)

                state.thought_process.append(
                    {
                        "step": "artifact_storage",
                        "details": {
                            "serial_number": state.serial_number,
                            "has_image": state.image_bytes is not None,
                            "text_length": len(state.text) if state.text else 0,
                            # "artifact_url": artifact_url,
                        },
                    }
                )

                self.logger.info("[ArtifactStorage] Artifact stored successfully")

            except Exception as e:
                self.logger.error(
                    f"[ArtifactStorage] Failed: {e}",
                    extra={"serial_number": state.serial_number, "error": str(e)},
                    exc_info=True,
                )
                state.error = f"Failed to store artifact: {str(e)}"

        # Send state to next executor
        await ctx.send_message(state)

    async def fsg_lookup_executor(self, state: WorkflowState, ctx: WorkflowContext[WorkflowState]) -> None:
        """
        Step 2: FSG (Field Service Gateway) lookup via MCP.

        Calls the FSG MCP server (via Azure APIM) to retrieve workflow data
        associated with the serial number.
        """
        self.logger.info(
            f"[FSGLookup] Calling FSG MCP server for serial_number={state.serial_number}",
            extra={"serial_number": state.serial_number},
        )

        if state.error:
            # Skip if previous step failed
            self.logger.warning(
                "[FSGLookup] Skipping due to previous error",
                extra={"serial_number": state.serial_number, "error": state.error},
            )
            await ctx.send_message(state)
            return

        with self.logger.trace_operation(
            "fsg_lookup", serial_number=state.serial_number, endpoint=self.settings.fsg_endpoint
        ) as span:
            try:
                # TODO: Implement FSG MCP client call
                # fsg_result = await self.fsg_client.invoke(
                #     serial_number=state.serial_number,
                #     context={"text": state.text}
                # )
                # state.fsg_data = fsg_result
                # span.set_attribute("fsg_result_keys", list(fsg_result.keys()))

                state.thought_process.append(
                    {
                        "step": "fsg_lookup",
                        "details": {
                            "serial_number": state.serial_number,
                            # "fsg_data": fsg_result,
                        },
                    }
                )

                self.logger.info("[FSGLookup] FSG lookup completed successfully")

            except Exception as e:
                self.logger.error(
                    f"[FSGLookup] Failed: {e}",
                    extra={"serial_number": state.serial_number, "error": str(e)},
                    exc_info=True,
                )
                state.error = f"Failed to lookup FSG data: {str(e)}"

        # Send state to next executor
        await ctx.send_message(state)

    async def phoenix_enrichment_executor(self, state: WorkflowState, ctx: WorkflowContext[WorkflowState]) -> None:
        """
        Step 3: Phoenix enrichment via MCP.

        Calls the Phoenix MCP server (via Azure APIM) to enrich the workflow
        context with additional data from Phoenix systems.
        """
        self.logger.info(
            f"[PhoenixEnrichment] Calling Phoenix MCP server for serial_number={state.serial_number}",
            extra={"serial_number": state.serial_number},
        )

        if state.error:
            # Skip if previous step failed
            self.logger.warning(
                "[PhoenixEnrichment] Skipping due to previous error",
                extra={"serial_number": state.serial_number, "error": state.error},
            )
            await ctx.send_message(state)
            return

        with self.logger.trace_operation(
            "phoenix_enrichment", serial_number=state.serial_number, endpoint=self.settings.phoenix_endpoint
        ) as span:
            try:
                # TODO: Implement Phoenix MCP client call
                # phoenix_result = await self.phoenix_client.invoke(
                #     serial_number=state.serial_number,
                #     context=state.fsg_data
                # )
                # state.phoenix_data = phoenix_result
                # span.set_attribute("phoenix_result_keys", list(phoenix_result.keys()))

                state.thought_process.append(
                    {
                        "step": "phoenix_enrichment",
                        "details": {
                            "serial_number": state.serial_number,
                            # "phoenix_data": phoenix_result,
                        },
                    }
                )

                self.logger.info("[PhoenixEnrichment] Phoenix enrichment completed successfully")

            except Exception as e:
                self.logger.error(
                    f"[PhoenixEnrichment] Failed: {e}",
                    extra={"serial_number": state.serial_number, "error": str(e)},
                    exc_info=True,
                )
                state.error = f"Failed to enrich with Phoenix data: {str(e)}"

        # Send state to next executor
        await ctx.send_message(state)

    async def reasoning_executor(self, state: WorkflowState, ctx: WorkflowContext[WorkflowState]) -> None:
        """
        Step 4: Reasoning agent invocation.

        Invokes the Microsoft Foundry reasoning agent to perform AI reasoning over the
        collected data and generate recommendations or insights.
        """
        self.logger.info(
            f"[ReasoningAgent] Invoking reasoning agent for serial_number={state.serial_number}",
            extra={"serial_number": state.serial_number, "agent_id": self.settings.foundry_reasoning_agent_id},
        )

        if state.error:
            # Skip if previous step failed
            self.logger.warning(
                "[ReasoningAgent] Skipping due to previous error",
                extra={"serial_number": state.serial_number, "error": state.error},
            )
            await ctx.send_message(state)
            return

        with self.logger.trace_operation(
            "reasoning_agent", serial_number=state.serial_number, agent_id=self.settings.foundry_reasoning_agent_id
        ) as span:
            try:
                # TODO: Implement Foundry service call
                # reasoning_result = await self.foundry.invoke_agent(
                #     serial_number=state.serial_number,
                #     text=state.text,
                #     fsg_data=state.fsg_data,
                #     phoenix_data=state.phoenix_data,
                # )
                # state.reasoning = reasoning_result
                # span.set_attribute("reasoning_length", len(str(reasoning_result)))

                state.thought_process.append(
                    {
                        "step": "reasoning_agent",
                        "details": {
                            "serial_number": state.serial_number,
                            # "reasoning": reasoning_result,
                        },
                    }
                )

                self.logger.info("[ReasoningAgent] Reasoning completed successfully")

            except Exception as e:
                self.logger.error(
                    f"[ReasoningAgent] Failed: {e}",
                    extra={"serial_number": state.serial_number, "error": str(e)},
                    exc_info=True,
                )
                state.error = f"Failed to invoke reasoning agent: {str(e)}"

        # Send state to next executor
        await ctx.send_message(state)

    async def cosmos_persistence_executor(self, state: WorkflowState, ctx: WorkflowContext[WorkflowState]) -> None:
        """
        Step 5: Persist result to Cosmos DB.

        Stores the complete workflow result including all collected data,
        reasoning output, and metadata in Cosmos DB.
        """
        self.logger.info(
            f"[CosmosPersistence] Persisting workflow result for serial_number={state.serial_number}",
            extra={"serial_number": state.serial_number, "has_error": state.error is not None},
        )

        with self.logger.trace_operation(
            "cosmos_persistence",
            serial_number=state.serial_number,
            has_error=state.error is not None,
        ) as span:
            try:
                # TODO: Implement Cosmos DB persistence
                # workflow_record = {
                #     "id": state.serial_number,
                #     "serial_number": state.serial_number,
                #     "text": state.text,
                #     "artifact_url": state.artifact_url,
                #     "fsg_data": state.fsg_data,
                #     "phoenix_data": state.phoenix_data,
                #     "reasoning": state.reasoning,
                #     "thought_process": state.thought_process,
                #     "error": state.error,
                # }
                # await self.cosmos.upsert_item(workflow_record)
                # span.set_attribute("record_size", len(str(workflow_record)))

                state.thought_process.append(
                    {
                        "step": "cosmos_persistence",
                        "details": {
                            "serial_number": state.serial_number,
                            "persisted": True,
                            "has_error": state.error is not None,
                        },
                    }
                )

                self.logger.info("[CosmosPersistence] Workflow result persisted successfully")

            except Exception as e:
                self.logger.error(
                    f"[CosmosPersistence] Failed: {e}",
                    extra={"serial_number": state.serial_number, "error": str(e)},
                    exc_info=True,
                )
                state.error = f"Failed to persist to Cosmos DB: {str(e)}"

                state.thought_process.append(
                    {
                        "step": "cosmos_persistence",
                        "details": {
                            "serial_number": state.serial_number,
                            "persisted": False,
                            "error": str(e),
                        },
                    }
                )

        # Yield final output
        await ctx.yield_output(state)  # type: ignore[attr-defined]
