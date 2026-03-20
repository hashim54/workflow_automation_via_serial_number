"""Mock API routes for FSG and Phoenix data served from Cosmos DB."""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException

from app.core.container import Container
from app.services.mock_cosmos_db_service import MockCosmosDBService

router = APIRouter()


@inject
def _get_mock_cosmos(
    service: MockCosmosDBService = Depends(Provide[Container.mock_cosmos]),
) -> MockCosmosDBService:
    return service


@router.get("/fsg/products/{serial_number}", tags=["mock"])
async def get_fsg_product(
    serial_number: str,
    mock_cosmos: MockCosmosDBService = Depends(_get_mock_cosmos),
) -> dict:
    """Return FSG product data for the given serial number."""
    result = await mock_cosmos.get_fsg_product(serial_number)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"FSG product not found for serial_number={serial_number}",
        )
    return result.get("payload", result)


@router.get("/phoenix/plm/serialnumber/{product_number}", tags=["mock"])
async def get_phoenix_product(
    product_number: str,
    mock_cosmos: MockCosmosDBService = Depends(_get_mock_cosmos),
) -> dict:
    """Return Phoenix product data for the given product number."""
    result = await mock_cosmos.get_phoenix_product(product_number)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Phoenix product not found for product_number={product_number}",
        )
    return result.get("payload", result)
