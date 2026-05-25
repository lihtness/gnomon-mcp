"""Entry point: `gnomon-mcp` runs the MCP server (stdio by default)."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from gnomon_mcp.server import mcp


def _run_demo() -> None:
    """Call each tool directly and print the result. No MCP client needed."""
    from gnomon_mcp.tools import calc_tools, calendar_tools

    def show(label: str, value: Any) -> None:
        print(f"\n>>> {label}")
        print(json.dumps(value, indent=2, default=str))

    print("gnomon-mcp demo — calling each tool directly:")

    show("now()", calendar_tools.now())
    show('now(tz="America/Los_Angeles")', calendar_tools.now("America/Los_Angeles"))

    show(
        "calendar([...batch of 6 ops...])",
        calendar_tools.calendar([
            {"op": "until", "target": "2026-12-31", "unit": "days"},
            {"op": "since", "source": "2026-01-01", "unit": "days"},
            {"op": "diff", "start": "2026-01-01", "end": "2026-12-31", "unit": "days"},
            {"op": "weekday", "date": "2026-05-25"},
            {"op": "add", "date": "2026-05-25", "n": 1, "unit": "months"},
            {"op": "business_days", "start": "2026-05-01", "end": "2026-06-01"},
        ]),
    )

    show(
        'calc(["2+3*4", "sqrt(16)", "mean([1,2,3,4])", "sum(range(101))"])',
        calc_tools.calc(["2+3*4", "sqrt(16)", "mean([1,2,3,4])", "sum(range(101))"]),
    )

    show(
        'calc_convert(100, "meter", "foot")',
        calc_tools.calc_convert(100, "meter", "foot"),
    )
    show(
        'calc_convert(0, "degC", "degF")',
        calc_tools.calc_convert(0, "degC", "degF"),
    )

    print("\n(demo done — wire gnomon into your agent and let it call these instead of guessing.)")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gnomon-mcp",
        description="Gnomon MCP server — deterministic dates, calendars, math, units for LLM agents.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport to serve over. Default: stdio (local subprocess MCP).",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind for HTTP/SSE transports. Default: 127.0.0.1.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind for HTTP/SSE transports. Default: 8000.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Skip the server; call each tool directly and print results. Useful for trying gnomon without an MCP client.",
    )
    args = parser.parse_args()

    if args.demo:
        _run_demo()
        return

    if args.transport != "stdio":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        print(
            f"gnomon-mcp serving {args.transport} on http://{args.host}:{args.port}",
            file=sys.stderr,
        )

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
