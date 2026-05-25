# gnomon-mcp

> The pointer on a sundial that turns shadow into time.

A small MCP server for the boring-but-essential utilities every model needs: dates, calendars, arithmetic, unit conversion. Use it so your assistant stops "next-token guessing" math and date math.

## Why

LLMs are bad at arithmetic and date math by default. They produce plausible answers that are often wrong by a small amount — exactly the kind of mistake that's hard to notice in a long response. `gnomon-mcp` exposes deterministic Python implementations through MCP so your model can compute instead of guess.

## Tools

### Calendar

One batch tool that dispatches over many operations. Each item in the input list picks its own op — designed for table-row workloads where you want one tool call for many heterogeneous date operations.

| Op | Params | Returns |
|---|---|---|
| `now` | `tz?` | current ISO datetime in `tz` (default UTC) |
| `diff` | `start, end, unit` | `end - start` as float (`seconds\|minutes\|hours\|days\|weeks`) |
| `add` | `date, n, unit` | ISO of `date + n units` (above units plus `months\|years`, calendar-aware) |
| `weekday` | `date` | `"Monday"`..`"Sunday"` |
| `business_days` | `start, end` | count of Mon-Fri days (start inclusive, end exclusive) |
| `parse` | `natural, tz?` | ISO from natural language ("next thursday", "in 3 hours") |
| `format` | `date, fmt` | strftime-formatted string |

Example:

```python
calendar([
  {"op": "weekday", "date": "2026-05-25"},                         # → "Monday"
  {"op": "diff", "start": "2026-01-01", "end": "2026-12-31", "unit": "days"},  # → 364.0
  {"op": "add", "date": "2026-05-25", "n": 1, "unit": "months"},  # → "2026-06-25T00:00:00"
  {"op": "parse", "natural": "next thursday", "tz": "America/Los_Angeles"},
])
```

### Calculator

| Tool | Purpose |
|---|---|
| `calc(expressions)` | Evaluate a list of Python expressions and return a list of results. Math (`sqrt`, `sin`, `log`, `pi`, `e`, ...), stats (`mean`, `median`, `stdev`, `variance`), and useful builtins (`abs`, `round`, `min`, `max`, `sum`, `range`, `sorted`, ...) are pre-loaded. Batch in / batch out, order preserved. |
| `calc_convert(value, from_unit, to_unit)` | Unit conversion via Pint (`meter` → `foot`, `kg` → `lb`, `degC` → `degF`, etc.). |

Examples:

```python
calc(["2 + 3 * 4"])                  # [14]
calc(["sqrt(16)", "sin(pi/2)"])      # [4.0, 1.0]
calc(["mean([1, 2, 3, 4])"])         # [2.5]
calc(["sum(range(101))"])            # [5050]
calc(["(25 / 100) * 100"])           # [25.0]
```

## Installation

```bash
pip install gnomon-mcp
```

Or from source:

```bash
git clone https://github.com/lihtness/gnomon-mcp
cd gnomon-mcp
pip install -e ".[dev]"
```

## Use with Claude Code

Add to `~/.claude.json` or a project `.mcp.json`:

```json
{
  "mcpServers": {
    "gnomon": {
      "command": "gnomon-mcp"
    }
  }
}
```

## Use with Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gnomon": {
      "command": "gnomon-mcp"
    }
  }
}
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
