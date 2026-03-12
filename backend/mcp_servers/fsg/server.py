"""
FSG MCP Server

Exposes FSG (Field Service Gateway) functionality as MCP tools.
This server will be registered with Azure APIM as an MCP endpoint.

Tools:
    - lookup_serial_number: Retrieve workflow data by serial number
    - validate_field_data: Validate field service data
"""

from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("fsg-server")


# TODO: Define tools using @mcp.tool() decorator
# Example:
# @mcp.tool()
# async def lookup_serial_number(serial_number: str) -> dict:
#     """Retrieve workflow data by serial number."""
#     pass


async def main() -> None:
    """Run the FSG MCP server."""
    # TODO: Start FastMCP server
    # await mcp.run()
    raise NotImplementedError


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
