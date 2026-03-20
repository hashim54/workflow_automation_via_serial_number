from app.api.routes.health import router as health_router
from app.api.routes.workflow import router as workflow_router
from app.api.routes.config import router as config_router
from app.api.routes.mock_api import router as mock_api_router

__all__ = ["health_router", "workflow_router", "config_router", "mock_api_router"]
