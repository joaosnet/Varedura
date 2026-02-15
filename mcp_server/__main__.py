"""Varedura MCP Server entry point — allows running with `python -m mcp_server`."""

from mcp_server.server import mcp

if __name__ == "__main__":
    mcp.run()
