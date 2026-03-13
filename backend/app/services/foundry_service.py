from __future__ import annotations

import base64
import json
import logging
from typing import Any, AsyncIterator, Optional

from app.core.settings import Settings
from azure.ai.agents.aio import AgentsClient
from azure.ai.agents.models import (
    AgentThreadCreationOptions,
    MessageImageUrlParam,
    MessageInputImageUrlBlock,
    MessageRole,
    ThreadMessageOptions,
)
from azure.identity.aio import DefaultAzureCredential

from prompts.templates import ImageAnalysisPrompts

logger = logging.getLogger(__name__)


class FoundryService:
    """
    Async Microsoft Foundry operations.

    Provides agent invocation capabilities via Microsoft Foundry.
    Uses DefaultAzureCredential for passwordless authentication.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize Foundry service.

        Args:
            settings: Application settings containing azure_ai_project_connection_string

        Note:
            Client is created lazily on first use to allow API startup
            even when Foundry is not configured.
        """
        self._settings = settings
        self._credential: Optional[DefaultAzureCredential] = None
        self._client: Optional[AgentsClient] = None

    def _ensure_client(self) -> AgentsClient:
        """Ensure Foundry agents client is initialized."""
        if self._client is None:
            endpoint = self._settings.azure_ai_project_endpoint
            if not endpoint:
                raise ValueError(
                    "Microsoft Foundry project endpoint is not configured. " "Please set FOUNDRY_PROJECT_ENDPOINT."
                )

            self._credential = DefaultAzureCredential()
            self._client = AgentsClient(endpoint=endpoint, credential=self._credential)
        return self._client

    async def close(self) -> None:
        """Close the underlying async AIProjectClient and credential, releasing all connections."""
        if self._client:
            await self._client.close()
        if self._credential:
            await self._credential.close()

    async def extract_from_image(
        self,
        image_bytes: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        """Send an image to the image processing agent and extract serial number data.

        Args:
            image_bytes: Raw image bytes.
            content_type: MIME type of the image (e.g. "image/png").

        Returns:
            Parsed JSON dict from the agent with serial_number, model_number, etc.
        """
        client = self._ensure_client()

        agent_id = self._settings.microsoft_foundry.image_processing_agent_id
        if not agent_id:
            raise ValueError("Image processing agent ID is not configured (FOUNDRY_IMAGE_PROCESSING_AGENT_ID).")

        # Encode image as base64 data URL
        b64 = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{content_type};base64,{b64}"

        user_prompt = ImageAnalysisPrompts.build_serial_extraction_prompt()

        # Build thread with multimodal message (text + image)
        thread_options = AgentThreadCreationOptions(
            messages=[
                ThreadMessageOptions(
                    role=MessageRole.USER,
                    content=[
                        {"type": "text", "text": user_prompt},
                        MessageInputImageUrlBlock(
                            image_url=MessageImageUrlParam(url=data_url, detail="high"),
                        ),
                    ],
                )
            ]
        )

        # Create thread, run agent, and poll until completion
        foundry = self._settings.microsoft_foundry
        run = await client.create_thread_and_process_run(
            agent_id=agent_id,
            thread=thread_options,
            model=foundry.image_processing_model,
            instructions=ImageAnalysisPrompts.SERIAL_NUMBER_EXTRACTION_SYSTEM_PROMPT,
        )

        if run.status != "completed":
            return {"error": f"Agent run finished with status: {run.status}"}

        # Retrieve the assistant's last text response
        messages = client.messages.list(thread_id=run.thread_id)
        async for msg in messages:
            if msg.role == MessageRole.AGENT:
                # Try text_messages helper first
                if msg.text_messages:
                    raw_text = msg.text_messages[-1].text.value
                    try:
                        return json.loads(raw_text)
                    except json.JSONDecodeError:
                        return {"raw_response": raw_text}
                # Fallback: iterate content blocks directly
                if msg.content:
                    for block in msg.content:
                        if hasattr(block, "text") and block.text:
                            raw_text = block.text.value
                            try:
                                return json.loads(raw_text)
                            except json.JSONDecodeError:
                                return {"raw_response": raw_text}
                break

        return {"error": "No assistant response received"}

    async def invoke_agent(
        self,
        agent_id: str,
        messages: list[dict[str, Any]],
        *,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Invoke a Foundry agent and wait for completion.

        Args:
            agent_id: Agent ID from Microsoft Foundry
            messages: List of message dictionaries with 'role' and 'content'
            thread_id: Optional existing thread ID (creates new if not provided)

        Returns:
            Agent response dictionary containing the result

        Example:
            >>> result = await foundry.invoke_agent(
            ...     agent_id="reasoning-agent-001",
            ...     messages=[
            ...         {"role": "user", "content": "Analyze this data..."}
            ...     ]
            ... )
        """
        client = self._ensure_client()

        if thread_id:
            # Add messages to existing thread, then run
            for message in messages:
                await client.messages.create(
                    thread_id=thread_id,
                    role=message.get("role", "user"),
                    content=message.get("content", ""),
                )
            run = await client.runs.create_and_process(
                thread_id=thread_id, agent_id=agent_id
            )
        else:
            # Create thread with messages and run in one call
            thread_options = AgentThreadCreationOptions(
                messages=[
                    ThreadMessageOptions(
                        role=message.get("role", "user"),
                        content=message.get("content", ""),
                    )
                    for message in messages
                ]
            )
            run = await client.create_thread_and_process_run(
                agent_id=agent_id, thread=thread_options
            )

        # Get latest assistant message
        last_msg = await client.messages.get_last_message_text_by_role(
            thread_id=run.thread_id, role=MessageRole.AGENT
        )

        return {
            "thread_id": run.thread_id,
            "run_id": run.id,
            "status": run.status,
            "content": last_msg.text.value if last_msg else None,
        }

    async def stream_agent(
        self,
        agent_id: str,
        messages: list[dict[str, Any]],
        *,
        thread_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Invoke a Foundry agent and stream response chunks.

        Args:
            agent_id: Agent ID from Microsoft Foundry
            messages: List of message dictionaries with 'role' and 'content'
            thread_id: Optional existing thread ID (creates new if not provided)

        Yields:
            Response chunks as dictionaries

        Example:
            >>> async for chunk in foundry.stream_agent(
            ...     agent_id="reasoning-agent-001",
            ...     messages=[{"role": "user", "content": "Analyze..."}]
            ... ):
            ...     print(chunk)
        """
        client = self._ensure_client()

        # Create or use existing thread
        if thread_id:
            tid = thread_id
        else:
            thread = await client.threads.create()
            tid = thread.id

        # Add messages to thread
        for message in messages:
            await client.messages.create(
                thread_id=tid, role=message.get("role", "user"), content=message.get("content", "")
            )

        # Create streaming run
        async with await client.runs.stream(
            thread_id=tid, agent_id=agent_id
        ) as event_handler:
            async for event_type, event_data, _ in event_handler:
                if hasattr(event_data, "delta") and event_data.delta:
                    if event_data.delta.content:
                        for block in event_data.delta.content:
                            if hasattr(block, "text") and block.text:
                                yield {
                                    "type": "content",
                                    "delta": block.text.value,
                                    "thread_id": tid,
                                }
                elif hasattr(event_data, "status") and event_data.status == "completed":
                    yield {
                        "type": "done",
                        "thread_id": tid,
                        "run_id": event_data.id,
                    }
