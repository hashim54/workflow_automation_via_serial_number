from __future__ import annotations

from typing import Any, AsyncIterator, Optional

from app.core.settings import Settings
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential


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
        self._client: Optional[AIProjectClient] = None

    def _ensure_client(self) -> AIProjectClient:
        """Ensure Foundry client is initialized."""
        if self._client is None:
            endpoint = self._settings.azure_ai_project_endpoint
            if not endpoint:
                raise ValueError(
                    "Microsoft Foundry project endpoint is not configured. " "Please set FOUNDRY_PROJECT_ENDPOINT."
                )

            self._credential = DefaultAzureCredential()
            self._client = AIProjectClient(endpoint=endpoint, credential=self._credential)
        return self._client

    async def close(self) -> None:
        """Close the underlying async AIProjectClient and credential, releasing all connections."""
        if self._client:
            await self._client.close()
        if self._credential:
            await self._credential.close()

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
        # Get agents client
        client = self._ensure_client()
        agents = client.agents  # type: ignore[attr-defined]

        # Create or use existing thread
        if thread_id:
            thread = await agents.get_thread(thread_id)  # type: ignore[attr-defined]
        else:
            thread = await agents.create_thread()  # type: ignore[attr-defined]

        # Add messages to thread
        for message in messages:
            await agents.create_message(  # type: ignore[attr-defined]
                thread_id=thread.id, role=message.get("role", "user"), content=message.get("content", "")
            )

        # Run agent
        run = await agents.create_run(thread_id=thread.id, assistant_id=agent_id)  # type: ignore[attr-defined]

        # Wait for completion
        while run.status in ["queued", "in_progress", "requires_action"]:
            await agents.wait_for_run(thread_id=thread.id, run_id=run.id)  # type: ignore[attr-defined]
            run = await agents.get_run(thread_id=thread.id, run_id=run.id)  # type: ignore[attr-defined]

        # Get messages
        messages_response = await agents.list_messages(thread_id=thread.id)  # type: ignore[attr-defined]

        # Extract latest assistant message
        latest_message = None
        for msg in messages_response.data:
            if msg.role == "assistant":
                latest_message = msg
                break

        return {
            "thread_id": thread.id,
            "run_id": run.id,
            "status": run.status,
            "content": latest_message.content[0].text.value if latest_message else None,
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
        # Get agents client
        client = self._ensure_client()
        agents = client.agents  # type: ignore[attr-defined]

        # Create or use existing thread
        if thread_id:
            thread = await agents.get_thread(thread_id)  # type: ignore[attr-defined]
        else:
            thread = await agents.create_thread()  # type: ignore[attr-defined]

        # Add messages to thread
        for message in messages:
            await agents.create_message(  # type: ignore[attr-defined]
                thread_id=thread.id, role=message.get("role", "user"), content=message.get("content", "")
            )

        # Create streaming run
        stream = await agents.create_run_stream(thread_id=thread.id, assistant_id=agent_id)  # type: ignore[attr-defined]

        # Stream events
        async for event in stream:
            if event.event == "thread.message.delta":
                if event.data and event.data.delta and event.data.delta.content:
                    for content in event.data.delta.content:
                        if hasattr(content, "text") and content.text:
                            yield {
                                "type": "content",
                                "delta": content.text.value,
                                "thread_id": thread.id,
                            }
            elif event.event == "thread.run.completed":
                yield {
                    "type": "done",
                    "thread_id": thread.id,
                    "run_id": event.data.id,
                }
