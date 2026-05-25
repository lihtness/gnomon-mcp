"""Entry point: `gnomon-mcp` runs the stdio MCP server."""
from gnomon_mcp.server import mcp


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
