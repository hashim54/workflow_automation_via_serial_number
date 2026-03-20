"""Mock Cosmos DB service for FSG and Phoenix mock API data.

Manages two Cosmos DB containers within a dedicated mock database:
- FSG container (partition key: /serial_number)
- Phoenix container (partition key: /lookup_product_input_product_number)

Supports optional initial data loading from JSON files on startup.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from app.core.settings import Settings
from azure.cosmos import PartitionKey
from azure.cosmos.aio import ContainerProxy, CosmosClient, DatabaseProxy
from azure.cosmos.exceptions import CosmosHttpResponseError
from azure.identity.aio import DefaultAzureCredential

MOCK_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "mock-data"


class MockCosmosDBService:
    """Async Cosmos DB service for mock FSG and Phoenix data.

    Uses a dedicated Cosmos endpoint if MOCK_COSMOS_ENDPOINT is set,
    otherwise falls back to the main Cosmos connection settings.
    """

    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self._settings = settings
        self._logger = logger
        self._credential: Optional[DefaultAzureCredential] = None
        self._client: Optional[CosmosClient] = None
        self._database: Optional[DatabaseProxy] = None
        self._fsg_container: Optional[ContainerProxy] = None
        self._phoenix_container: Optional[ContainerProxy] = None

    def _ensure_client(self) -> CosmosClient:
        """Lazily initialize the Cosmos client.

        Prefers mock-specific settings (MOCK_COSMOS_ENDPOINT / MOCK_COSMOS_CONNECTION_STRING).
        Falls back to the main Cosmos settings when mock-specific ones are not set.
        """
        if self._client is None:
            mock_opts = self._settings.mock_options.cosmos
            cosmos_opts = self._settings.cosmos_db_options

            # Try mock-specific connection first, then fall back to main Cosmos settings
            conn_str = mock_opts.connection_string or cosmos_opts.connection_string
            endpoint = mock_opts.endpoint or cosmos_opts.endpoint

            if conn_str:
                self._client = CosmosClient.from_connection_string(conn_str)
                self._logger.info("[MockCosmos] Client initialized via connection string")
            elif endpoint:
                self._credential = DefaultAzureCredential()
                self._client = CosmosClient(endpoint, credential=self._credential)
                # Mask endpoint for logging (show host only)
                masked = endpoint.split("//")[-1].rstrip("/")
                self._logger.info(f"[MockCosmos] Client initialized via endpoint: {masked}")
            else:
                raise ValueError(
                    "Mock Cosmos DB is not configured. "
                    "Set MOCK_COSMOS_ENDPOINT / MOCK_COSMOS_CONNECTION_STRING "
                    "or COSMOS_ENDPOINT / COSMOS_CONNECTION_STRING."
                )
        return self._client

    def _get_fsg_container(self) -> ContainerProxy:
        if self._fsg_container is None:
            client = self._ensure_client()
            mock_opts = self._settings.mock_options.cosmos
            self._database = client.get_database_client(mock_opts.database_name)
            self._fsg_container = self._database.get_container_client(mock_opts.fsg_container_name)
        return self._fsg_container

    def _get_phoenix_container(self) -> ContainerProxy:
        if self._phoenix_container is None:
            client = self._ensure_client()
            mock_opts = self._settings.mock_options.cosmos
            self._database = client.get_database_client(mock_opts.database_name)
            self._phoenix_container = self._database.get_container_client(mock_opts.phoenix_container_name)
        return self._phoenix_container

    async def ensure_containers(self) -> None:
        """Create mock database and containers if they don't exist."""
        client = self._ensure_client()
        mock_opts = self._settings.mock_options.cosmos

        db = await client.create_database_if_not_exists(id=mock_opts.database_name)
        self._logger.info(f"[MockCosmos] Database ready: {mock_opts.database_name}")

        # FSG container — partition key: /serial_number
        fsg_pk = PartitionKey(path="/serial_number")
        await db.create_container_if_not_exists(
            id=mock_opts.fsg_container_name,
            partition_key=fsg_pk,
        )
        self._logger.info(
            f"[MockCosmos] Container ready: {mock_opts.fsg_container_name} (PK=/serial_number)"
        )

        # Phoenix container — partition key: /lookup_product_input_product_number
        phoenix_pk = PartitionKey(path="/lookup_product_input_product_number")
        await db.create_container_if_not_exists(
            id=mock_opts.phoenix_container_name,
            partition_key=phoenix_pk,
        )
        self._logger.info(
            f"[MockCosmos] Container ready: {mock_opts.phoenix_container_name} "
            f"(PK=/lookup_product_input_product_number)"
        )

    async def load_initial_data(self) -> None:
        """Load FSG and Phoenix seed data from JSON files into Cosmos DB.

        Uses upsert so the operation is idempotent.
        """
        self._logger.info(f"[MockCosmos] Source directory: {MOCK_DATA_DIR}")
        await self._load_json_into_container(
            json_path=MOCK_DATA_DIR / "fsg.json",
            container=self._get_fsg_container(),
            label="FSG",
        )
        await self._load_json_into_container(
            json_path=MOCK_DATA_DIR / "phoenix.json",
            container=self._get_phoenix_container(),
            label="Phoenix",
        )
        self._logger.info("[MockCosmos] Initial data loading complete")

    async def _load_json_into_container(
        self,
        json_path: Path,
        container: ContainerProxy,
        label: str,
    ) -> None:
        if not json_path.exists():
            self._logger.warning(f"[MockCosmos] Seed file not found: {json_path}")
            return

        raw = json_path.read_text(encoding="utf-8")
        file_size_kb = len(raw.encode("utf-8")) / 1024
        items: list[dict[str, Any]] = json.loads(raw)
        self._logger.info(
            f"[MockCosmos] Loading {label} data from {json_path.name} "
            f"({len(items)} documents, {file_size_kb:.1f} KB)..."
        )

        start = time.monotonic()
        count = 0
        for item in items:
            await container.upsert_item(body=item)
            count += 1
            self._logger.debug(f"[MockCosmos]   Upserted {label} document: {item.get('id', '?')}")
        elapsed = time.monotonic() - start
        self._logger.info(f"[MockCosmos] Loaded {count} {label} documents in {elapsed:.2f}s")

    async def get_fsg_product(self, serial_number: str) -> Optional[dict[str, Any]]:
        """Look up an FSG product by serial number (point read)."""
        container = self._get_fsg_container()
        item_id = f"fsg_{serial_number}"
        try:
            return await container.read_item(item=item_id, partition_key=serial_number)
        except CosmosHttpResponseError as exc:
            if exc.status_code == 404:
                return None
            raise

    async def get_phoenix_product(self, product_number: str) -> Optional[dict[str, Any]]:
        """Look up a Phoenix product by product number (point read)."""
        container = self._get_phoenix_container()
        item_id = f"phoenix_{product_number}"
        try:
            return await container.read_item(item=item_id, partition_key=product_number)
        except CosmosHttpResponseError as exc:
            if exc.status_code == 404:
                return None
            raise

    async def close(self) -> None:
        """Release Cosmos client and credential resources."""
        if self._client:
            await self._client.close()
        if self._credential:
            await self._credential.close()
