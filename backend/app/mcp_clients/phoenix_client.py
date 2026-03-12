from app.core.settings import Settings


class PhoenixClient:
    """
    MCP Client — Phoenix.
    Makes a deterministic call to the Phoenix MCP Server via Azure APIM
    to validate or enrich workflow context for a given serial number.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def invoke(self, serial_number: str, context: dict) -> dict:
        # TODO: call Phoenix MCP server endpoint via APIM (self._settings.phoenix_api_endpoint)
        raise NotImplementedError
