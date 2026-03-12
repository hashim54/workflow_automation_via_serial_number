from app.core.settings import Settings


class FsgClient:
    """
    MCP Client — FSG (Field Service Gateway).
    Makes a deterministic call to the FSG MCP Server via Azure APIM
    to retrieve workflow data for a given serial number.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def invoke(self, serial_number: str, context: dict) -> dict:
        # TODO: call FSG MCP server endpoint via APIM (self._settings.fsg_endpoint)
        raise NotImplementedError
