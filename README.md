# gnomon-mcp

> The pointer on a sundial that turns shadow into time.

A small MCP server for the boring-but-essential utilities every model needs: dates, calendars, arithmetic, unit conversion. Use it so your assistant stops "next-token guessing" math and date math.

## Why

LLMs are bad at arithmetic and date math by default. They produce plausible answers that are often wrong by a small amount — exactly the kind of mistake that's hard to notice in a long response. `gnomon-mcp` exposes deterministic Python implementations through MCP so your model can compute instead of guess.

## Tools

### Calendar

Two tools:

- **`now(tz?)`** — standalone. Returns a rich dict snapshot of the current moment. One call gets you everything about "right now".
- **`calendar(ops)`** — batch dispatcher. Each item picks its own op. Designed for table-row workloads (e.g. one call computes time-elapsed for every row).

**`now(tz?)`** returns:

```python
{
  "iso": "2026-05-25T14:30:45+00:00",
  "date": "2026-05-25",
  "time": "14:30:45",
  "unix": 1779345045,
  "tz": "UTC",
  "year": 2026, "month": 5, "month_name": "May", "day": 25,
  "weekday": "Monday", "weekday_num": 0,          # 0=Monday
  "day_of_year": 145, "week_of_year": 22,         # ISO week
  "quarter": 2, "fiscal_year_us_gov": 2026,       # FY starts Oct 1
  "hour": 14, "minute": 30, "second": 45,
  "is_weekend": False,
}
```

**`calendar(ops)`** operations:

| Op | Params | Returns |
|---|---|---|
| `diff` | `start, end, unit` | `end - start` — time elapsed between two known dates |
| `until` | `target, unit, tz?` | `target - now` — time left to a future point (negative if past) |
| `since` | `source, unit, tz?` | `now - source` — time elapsed since a past point (negative if future) |
| `add` | `date, n, unit` | ISO of `date + n units` (`seconds\|...\|weeks`, plus `months\|years` calendar-aware) |
| `weekday` | `date` | `"Monday"`..`"Sunday"` |
| `business_days` | `start, end` | count of Mon-Fri days (start inclusive, end exclusive) |
| `parse` | `natural, tz?` | ISO from natural language ("next thursday", "in 3 hours") |
| `format` | `date, fmt` | strftime-formatted string |

Units for `diff`/`until`/`since`: `seconds`, `minutes`, `hours`, `days`, `weeks`.

Example — compute several things in one call:

```python
calendar([
  {"op": "until", "target": "2026-12-31", "unit": "days"},          # days left in year
  {"op": "since", "source": "2026-01-01", "unit": "days"},          # days elapsed in year
  {"op": "diff", "start": "2026-01-01", "end": "2026-12-31", "unit": "days"},
  {"op": "weekday", "date": "2026-05-25"},                           # "Monday"
  {"op": "add", "date": "2026-05-25", "n": 1, "unit": "months"},
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
