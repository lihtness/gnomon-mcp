"""Gnomon MCP server — registers the batch calendar and calc tools with FastMCP."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from gnomon_mcp.tools import calc_tools, calendar_tools

mcp = FastMCP("gnomon")

mcp.tool()(calendar_tools.now)
mcp.tool()(calendar_tools.calendar)
mcp.tool()(calc_tools.calc)
mcp.tool()(calc_tools.calc_convert)
