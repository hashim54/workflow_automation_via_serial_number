from __future__ import annotations

from typing import Any, AsyncIterator, Optional

from app.core.settings import Settings
from azure.cosmos.aio import ContainerProxy, CosmosClient, DatabaseProxy
from azure.cosmos.exceptions import CosmosHttpResponseError
from azure.identity.aio import DefaultAzureCredential


class CosmosDBService:
    """
    Async Cosmos DB operations using azure.cosmos.aio.

    Provides CRUD operations and queries for workflow records in Azure Cosmos DB.
    Uses DefaultAzureCredential for passwordless authentication.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize Cosmos DB service with settings.

        Args:
            settings: Application settings containing cosmos_endpoint, cosmos_database, cosmos_container

        Note:
            Clients are created lazily on first use to allow API startup
            even when Cosmos DB is not configured.
        """
        self._settings = settings
        self._credential: Optional[DefaultAzureCredential] = None
        self._client: Optional[CosmosClient] = None
        self._database: Optional[DatabaseProxy] = None
        self._container: Optional[ContainerProxy] = None

    def _ensure_client(self) -> ContainerProxy:
        """Ensure Cosmos DB client is initialized."""
        if self._container is None:
            if not self._settings.cosmos_endpoint:
                raise ValueError("Cosmos DB endpoint is not configured")
            self._credential = DefaultAzureCredential()
            self._client = CosmosClient(self._settings.cosmos_endpoint, credential=self._credential)
            self._database = self._client.get_database_client(self._settings.cosmos_database)
            self._container = self._database.get_container_client(self._settings.cosmos_container)
        return self._container

    async def close(self) -> None:
        """Close the underlying async CosmosClient and credential, releasing all connections."""
        if self._client:
            await self._client.close()
        if self._credential:
            await self._credential.close()

    async def create_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new item in Cosmos DB.

        Args:
            item: Document to create

        Returns:
            Created document with system properties

        Raises:
            CosmosHttpResponseError: If item already exists or other error occurs
        """
        container = self._ensure_client()
        return await container.create_item(body=item)

    async def upsert_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """
        Create or update an item in Cosmos DB.

        Args:
            item: Document to upsert (must contain 'id' and partition key)

        Returns:
            Upserted document with system properties
        """
        container = self._ensure_client()
        return await container.upsert_item(body=item)

    async def read_item(self, *, item_id: str, partition_key: list[str]) -> dict[str, Any]:
        """
        Read a specific item by ID and partition key.

        Args:
            item_id: Document ID
            partition_key: HPK value as a list, e.g. [user_id, serial_number]

        Returns:
            Document from Cosmos DB

        Raises:
            CosmosHttpResponseError: If item not found (404) or other error
        """
        container = self._ensure_client()
        return await container.read_item(item=item_id, partition_key=partition_key)

    async def replace_item(self, *, item_id: str, item: dict[str, Any]) -> dict[str, Any]:
        """
        Replace an existing item completely.

        Args:
            item_id: Document ID to replace
            item: New document content

        Returns:
            Replaced document with system properties

        Raises:
            CosmosHttpResponseError: If item not found or other error
        """
        container = self._ensure_client()
        return await container.replace_item(item=item_id, body=item)

    async def patch_item(
        self,
        *,
        item_id: str,
        partition_key: list[str],
        patch_operations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Partially update an item using patch operations.

        Args:
            item_id: Document ID
            partition_key: HPK value as a list, e.g. [user_id, serial_number]
            patch_operations: List of patch operation dictionaries

        Returns:
            Patched document

        Example:
            >>> patch_ops = [
            ...     {"op": "add", "path": "/status", "value": "completed"},
            ...     {"op": "replace", "path": "/updated_at", "value": "2024-03-11T10:00:00Z"}
            ... ]
            >>> await cosmos.patch_item(item_id="123", partition_key=["user1", "SN-001"], patch_operations=patch_ops)
        """
        container = self._ensure_client()
        return await container.patch_item(
            item=item_id,
            partition_key=partition_key,
            patch_operations=patch_operations,
        )

    async def delete_item(self, *, item_id: str, partition_key: list[str]) -> None:
        """
        Delete an item from Cosmos DB.

        Args:
            item_id: Document ID
            partition_key: HPK value as a list, e.g. [user_id, serial_number]

        Raises:
            CosmosHttpResponseError: If item not found or other error
        """
        container = self._ensure_client()
        await container.delete_item(item=item_id, partition_key=partition_key)

    def query_items(
        self,
        query: str,
        parameters: list[dict[str, Any]] | None = None,
        *,
        max_item_count: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Query items using SQL-like syntax.

        Returns an AsyncItemPaged iterator that must be used with ``async for``.

        Args:
            query: SQL query string (e.g., "SELECT * FROM c WHERE c.status = @status")
            parameters: Query parameters (e.g., [{"name": "@status", "value": "active"}])
            max_item_count: Maximum items per page (optional)

        Returns:
            AsyncIterator yielding matching documents

        Example:
            >>> async for item in cosmos.query_items(
            ...     query="SELECT * FROM c WHERE c.serial_number = @sn",
            ...     parameters=[{"name": "@sn", "value": "ABC123"}]
            ... ):
            ...     print(item)

        Note:
            Cross-partition queries are enabled by default in azure.cosmos.aio SDK v4+.
        """
        container = self._ensure_client()
        kwargs: dict[str, Any] = {"query": query, "parameters": parameters}
        if max_item_count is not None:
            kwargs["max_item_count"] = max_item_count
        return container.query_items(**kwargs)

    @staticmethod
    def is_not_found_error(ex: Exception) -> bool:
        """
        Check if an exception is a Cosmos DB 404 Not Found error.

        Args:
            ex: Exception to check

        Returns:
            True if exception is a 404 error, False otherwise

        Example:
            >>> try:
            ...     item = await cosmos.read_item(item_id="123", partition_key="user1")
            ... except Exception as e:
            ...     if CosmosDBService.is_not_found_error(e):
            ...         # Handle not found
            ...         pass
        """
        return isinstance(ex, CosmosHttpResponseError) and getattr(ex, "status_code", None) == 404
