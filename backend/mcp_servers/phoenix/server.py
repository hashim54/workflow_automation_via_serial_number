"""
Phoenix MCP Server

Exposes Phoenix system functionality as MCP tools.
This server will be registered with Azure APIM as an MCP endpoint.

Tools:
    - enrich_workflow_context: Add Phoenix context to workflow data
    - validate_serial_number: Validate serial number against Phoenix records
"""

from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("phoenix-server")


# TODO: Define tools using @mcp.tool() decorator
# Example:
# @mcp.tool()
# async def enrich_workflow_context(serial_number: str, context: dict) -> dict:
#     """Add Phoenix context to workflow data."""
#     pass


async def main() -> None:
    """Run the Phoenix MCP server."""
    # TODO: Start FastMCP server
    # await mcp.run()
    raise NotImplementedError


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
