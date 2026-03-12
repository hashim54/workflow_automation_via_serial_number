"""Dependency injection container."""

from dependency_injector import containers, providers

from app.core.settings import Settings
from app.core.logger import get_logger
from app.services.blob_storage_service import BlobStorageService
from app.services.cosmos_db_service import CosmosDBService
from app.services.foundry_service import FoundryService
from app.services.workflow_service import WorkflowService
from app.mcp_clients.fsg_client import FsgClient
from app.mcp_clients.phoenix_client import PhoenixClient
from app.workflows.core import SerialNumberWorkflow


class Container(containers.DeclarativeContainer):
    """Application dependency injection container."""
    
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.api.routes.workflow",
            "app.api.routes.health",
        ]
    )

    settings = providers.Singleton(Settings)

    # Logger
    logger = providers.Singleton(
        get_logger,
        name="workflow_automation",
        connection_string=settings.provided.applicationinsights_connection_string,
    )

    # Services (created but may not be fully configured)
    cosmos = providers.Singleton(CosmosDBService, settings=settings)
    blob_storage = providers.Singleton(BlobStorageService, settings=settings)
    foundry = providers.Singleton(FoundryService, settings=settings)

    # MCP Clients
    fsg_client = providers.Factory(FsgClient, settings=settings)
    phoenix_client = providers.Factory(PhoenixClient, settings=settings)

    # Workflow (may not be fully functional until services are configured)
    serial_number_workflow = providers.Factory(
        SerialNumberWorkflow,
        settings=settings,
        logger=logger,
        blob_storage=blob_storage,
        cosmos=cosmos,
        foundry=foundry,
        fsg_client=fsg_client,
        phoenix_client=phoenix_client,
    )

    # Top-level service used by API routes
    # WorkflowService validates configuration before execution
    workflow_service = providers.Factory(
        WorkflowService,
        settings=settings,
        workflow=serial_number_workflow,
    )
