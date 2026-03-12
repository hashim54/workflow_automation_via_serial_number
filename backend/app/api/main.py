"""FastAPI application entry point for Workflow Automation via Serial Number.

This module initializes the FastAPI application with routes, middleware,
and dependency injection for the Workflow Automation API.

Features:
    - FastAPI app with CORS middleware and error handling
    - Route modules: workflow execution, health checks, and configuration status
    - Dependency injection container for service management
    - Pydantic settings with environment variable configuration
    - Application lifecycle management (startup/shutdown)

Routes:
    - /api/v1/workflows: Workflow execution and status endpoints
    - /health: Health check and readiness probes
    - /config: Configuration validation and status

API Documentation:
    - Swagger UI: http://localhost:8000/docs
    - ReDoc: http://localhost:8000/redoc
    - OpenAPI JSON: http://localhost:8000/openapi.json
"""

import os
from contextlib import asynccontextmanager

from app.api.routes import config, health, workflow
from app.core.container import Container
from azure.cosmos import PartitionKey
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from agent_framework.azure import AzureAIClient
    from azure.ai.projects.aio import AIProjectClient
    from azure.identity.aio import DefaultAzureCredential

    FOUNDRY_PROJECT_AVAILABLE = True
except ImportError:
    FOUNDRY_PROJECT_AVAILABLE = False


# Initialize dependency injection container (singleton)
# This container is shared across all route modules
container = Container()
logger = container.logger()

# Export container for use in route modules
__all__ = ["app", "container", "logger"]

_SECONDS_PER_DAY: int = 24 * 60 * 60


async def _configure_foundry_telemetry() -> None:
    """Configure Azure AI Foundry Project telemetry.

    Integrates with the Azure AI Foundry Portal for end-to-end tracing.
    Called during FastAPI app startup.
    """
    if not FOUNDRY_PROJECT_AVAILABLE:
        logger.debug("Foundry Project Client not available. Install with: pip install azure-ai-projects")
        return

    project_endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    if not project_endpoint:
        logger.debug("FOUNDRY_PROJECT_ENDPOINT not set. Skipping Foundry telemetry setup.")
        return

    try:
        async with (
            DefaultAzureCredential() as credential,
            AIProjectClient(endpoint=project_endpoint, credential=credential) as project_client,
            AzureAIClient(project_client=project_client) as client,
        ):
            # Automatically configures Azure Monitor with connection string from project
            await client.configure_azure_monitor(enable_live_metrics=True)

        logger.info(f"✓ Foundry Project telemetry configured from {project_endpoint}")

    except Exception as e:
        logger.warning(
            f"Failed to configure Foundry Project telemetry: {e}. "
            f"Traces will use APPINSIGHTS_CONNECTION_STRING if available."
        )


async def _ensure_cosmos_resources() -> None:
    """Create Cosmos DB database and container if they don't exist.

    Called during FastAPI app startup to provision required Cosmos DB resources.
    """
    settings = container.settings()
    cosmos_options = settings.cosmos_db_options

    if not (cosmos_options.connection_string or cosmos_options.endpoint):
        logger.warning("Cosmos DB not configured - skipping workflow persistence setup")
        return

    try:
        logger.info("Ensuring Cosmos DB resources exist...")
        cosmos_service = container.cosmos()

        # Get the Cosmos client (this will trigger lazy initialization)
        cosmos_client = cosmos_service._client
        if not cosmos_client:
            logger.warning("Cosmos DB client not available - cannot provision resources")
            return

        # Create database
        db = await cosmos_client.create_database_if_not_exists(id=cosmos_options.database_name)
        logger.info(f"[Cosmos] Database ready: {cosmos_options.database_name}")

        # Container properties
        container_kwargs: dict = {}
        if cosmos_options.enable_ttl:
            container_kwargs["default_ttl"] = cosmos_options.default_ttl_days * 86400  # convert days to seconds

        # Indexing policy: optimize for workflow queries
        indexing_policy = {
            "indexingMode": "consistent",
            "automatic": True,
            "includedPaths": [{"path": "/*"}],
            "excludedPaths": [{"path": "/artifacts/?"}],  # Exclude large artifact arrays
        }

        # Hierarchical Partition Key (HPK): /user_id -> /serial_number
        # Overcomes the 20 GB single-partition limit and supports targeted multi-partition queries
        partition_key = PartitionKey(path=cosmos_options.partition_key_paths, kind="MultiHash", version=2)

        await db.create_container_if_not_exists(
            id=cosmos_options.container_name,
            partition_key=partition_key,
            indexing_policy=indexing_policy,
            **container_kwargs,
        )
        logger.info(
            f"[Cosmos] Container ready: {cosmos_options.container_name} "
            f"(HPK={cosmos_options.partition_key_paths}, "
            f"TTL={'enabled, ' + str(cosmos_options.default_ttl_days) + 'd' if cosmos_options.enable_ttl else 'disabled'})"
        )

    except Exception as e:
        logger.error(f"Failed to provision Cosmos DB resources: {e}")
        # raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle (startup and shutdown).

    Args:
        app: FastAPI application instance.
    """
    # Startup
    logger.info("Workflow Automation API starting up...")
    try:
        # Verify settings can be loaded
        settings = container.settings()
        logger.info("Configuration loaded successfully:")
        logger.info(f"  Environment: {os.getenv('ENVIRONMENT', 'development')}")
        logger.info(
            f"  Cosmos DB: {'Configured' if settings.cosmos_db_options.endpoint or settings.cosmos_db_options.connection_string else 'Not configured'}"
        )
        logger.info(
            f"  Blob Storage: {'Configured' if settings.blob_storage_options.account_url or settings.blob_storage_options.connection_string else 'Not configured'}"
        )
        logger.info(
            f"  Foundry Project: {'Configured' if settings.microsoft_foundry_options.project_endpoint else 'Not configured'}"
        )
        logger.info(
            f"  Application Insights: {'Configured' if settings.app_insights_options.connection_string else 'Not configured'}"
        )
        logger.info(f"  MCP FSG: {'Configured' if settings.mcp_client_options.fsg_endpoint else 'Not configured'}")
        logger.info(
            f"  MCP Phoenix: {'Configured' if settings.mcp_client_options.phoenix_endpoint else 'Not configured'}"
        )

        # Provision Cosmos DB resources if they don't exist
        await _ensure_cosmos_resources()

        # Configure Foundry Project telemetry (must be done in async context)
        await _configure_foundry_telemetry()

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

    yield

    # Shutdown
    logger.info("Workflow Automation API shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured ``FastAPI`` application instance.
    """
    app = FastAPI(
        title="Workflow Automation API",
        description="Automated workflow processing via serial number with Azure AI agents and MCP tools",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Attach container for dependency injection in routes
    app.container = container  # type: ignore[attr-defined]

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure based on your security requirements
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(workflow.router, prefix="/api/v1/workflows", tags=["workflows"])
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(config.router, prefix="/config", tags=["config"])

    return app


# Create app instance
app = create_app()
