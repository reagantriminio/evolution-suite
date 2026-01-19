#!/usr/bin/env python3
"""MCP Server runner for Evolution Suite.

This script runs the MCP server via stdio, allowing Claude Code to connect and use
the evolution-suite agent management tools.

Usage:
    python -m evolution_suite.mcp.server

Environment variables:
    EVOLUTION_SUITE_API_URL: Base URL for the evolution-suite API (default: http://localhost:8000/api)
"""

import asyncio
import sys

from mcp.server.stdio import stdio_server

from evolution_suite.mcp.agent_tools import create_mcp_server


async def main():
    """Run the MCP server."""
    server = create_mcp_server()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
