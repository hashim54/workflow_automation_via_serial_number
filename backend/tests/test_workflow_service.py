import pytest

from app.core.settings import Settings
from app.services.workflow_service import WorkflowService


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def workflow_service(settings: Settings) -> WorkflowService:
    return WorkflowService(settings=settings)


@pytest.mark.unit
class TestWorkflowService:
    # TODO: Add unit tests
    pass
