# gnomon-mcp

<!-- mcp-name: io.github.lihtness/gnomon-mcp -->

[![PyPI](https://img.shields.io/pypi/v/gnomon-mcp.svg)](https://pypi.org/project/gnomon-mcp/) [![Python](https://img.shields.io/pypi/pyversions/gnomon-mcp.svg)](https://pypi.org/project/gnomon-mcp/) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![MCP Registry](https://img.shields.io/badge/MCP%20Registry-io.github.lihtness%2Fgnomon--mcp-7c3aed)](https://registry.modelcontextprotocol.io/v0/servers?search=gnomon)

> The pointer on a sundial that turns shadow into time.

A small MCP server for the boring-but-essential utilities every model needs: dates, calendars, arithmetic, unit conversion. Use it so your assistant stops "next-token guessing" math and date math.

## Why

LLMs are bad at arithmetic and date math by default. They produce plausible answers that are often wrong by a small amount — exactly the kind of mistake that's hard to notice in a long response. `gnomon-mcp` exposes deterministic Python implementations through MCP so your model can compute instead of guess.

### When an agent should reach for gnomon

Anywhere the next plausible token is not the right answer. Concretely:

- **Math that matters** — anything beyond trivial mental arithmetic, anything with a decimal point, anything that compounds. Call `calc`.
- **"What day is it" / "how long until" / "how long since"** — the model's training cutoff is not today. Call `now` for a snapshot; `calendar` with `until`/`since`/`diff` for elapsed time; `parse` for natural-language dates ("next thursday").
- **Date arithmetic across month/year boundaries** — adding 30 days, finding a quarter-end, counting business days. Models routinely off-by-one these. Call `calendar` with `add` / `business_days`.
- **Unit conversion** — call `calc_convert`. Never eyeball "kg → lb" or "°C → °F".
- **Table-row workloads** — when the same kind of computation needs to run on every row of a table, both batch tools (`calendar`, `calc`) take a list and return a list in order. One call, N results.

The rule of thumb: if you'd ask a colleague to "just double-check that number," call gnomon instead.

### How this compares to other MCP servers

Time and math already have several MCP servers — the official [`Time`](https://github.com/modelcontextprotocol/servers-archived/tree/main/src/time) reference (timezone-only), [`mcp-time`](https://github.com/TheoBrigitte/mcp-time) and [`mcp-datetime`](https://github.com/ZeparHyfar/mcp-datetime) (date formatting / timezone), [`calculator-server`](https://github.com/avisangle/calculator-server) (math + units, no dates), and bundles like [`agent-utils-mcp`](https://github.com/aparajithn/agent-utils-mcp) (regex / hashing / JWT). gnomon's lane is narrower:

- **Batch-first.** `calendar(ops)` and `calc(expressions)` take lists; one tool call covers a whole table column instead of N calls.
- **A real `now()`.** One call returns 18 fields — ISO week, quarter, fiscal year, day-of-year, `is_weekend`, … — instead of just `{iso, tz}`.
- **Dates *and* math *and* units in one wiring.** No need to compose three separate servers.
- **Natural-language dates baked in** (`"next thursday"`, `"in 3 hours"`) without a separate NLP server.

If you only need timezone conversion, the official `Time` server is enough. If you want a broad utility bundle (regex, hashing, encoding, JWT), `agent-utils-mcp` is a better fit. gnomon is for the boring date-arithmetic-and-arithmetic core, batched.

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

## Future tools (sketches)

The same logic — *if the model is likely to bluff it, expose a deterministic version* — points at several more primitives worth building. None of these are implemented yet; they are candidates, listed roughly in order of bang-for-buck:

1. **Text measurement** — `count(text, unit)` for chars / words / lines / sentences / LLM tokens. Agents constantly miscount "how long is this" and "will this fit in the context window."
2. **Regex match / replace** — `regex_find(pattern, text)` and `regex_sub(pattern, repl, text)`. Models hallucinate which substrings match a regex; a real engine ends the argument.
3. **Structured-data extraction** — `jq(path, json)` / `jsonpath(path, json)`. Reading values out of a nested blob by path, without typos.
4. **Hashing & encoding** — `hash(text, algo)` (sha256, md5, blake2), `encode(text, scheme)` / `decode(text, scheme)` (base64, hex, url, jwt-payload). All things models confidently invent wrong.
5. **Decimal money math** — `money(expr)` evaluated under Python's `Decimal` with explicit rounding. `calc` is float-based and quietly unsafe for currency.
6. **Holiday-aware business days** — extend `calendar.business_days` with a `country` (or `calendar`) parameter so US/UK/IN holidays are excluded. The current implementation only knows weekends.
7. **Cron describe / next-fire** — `cron_describe("0 9 * * 1-5")` → human English; `cron_next(expr, n)` → next N firing times. Models routinely misread cron fields.
8. **Token counting for a target model** — `count_tokens(text, model)` via tiktoken / Anthropic tokenizer. Lets an agent budget its own prompts and outputs instead of guessing.

If you want one of these, open an issue (or a PR — each is a small self-contained module that fits the existing `tools/` layout).

## Install

Recommended: no install — run on demand via [`uv`](https://docs.astral.sh/uv/):

```bash
uvx gnomon-mcp           # serves stdio MCP, ready for any client
uvx gnomon-mcp --demo    # call every tool once and print the results (no MCP client needed)
```

Or install globally:

```bash
pip install gnomon-mcp
```

## Wire it into your agent

All recipes assume `uvx gnomon-mcp`. If you prefer a pinned install, swap the command for `gnomon-mcp` (with no `uvx`).

### Claude Code

```bash
claude mcp add gnomon -- uvx gnomon-mcp
```

Or edit `~/.claude.json` / a project `.mcp.json`:

```json
{
  "mcpServers": {
    "gnomon": { "command": "uvx", "args": ["gnomon-mcp"] }
  }
}
```

### Claude Desktop

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gnomon": { "command": "uvx", "args": ["gnomon-mcp"] }
  }
}
```

### Cursor

`~/.cursor/mcp.json` (or `.cursor/mcp.json` in a project):

```json
{
  "mcpServers": {
    "gnomon": { "command": "uvx", "args": ["gnomon-mcp"] }
  }
}
```

### Continue

`~/.continue/config.yaml`:

```yaml
mcpServers:
  - name: gnomon
    command: uvx
    args: ["gnomon-mcp"]
```

### Any other client (generic stdio)

Spawn `uvx gnomon-mcp` as a subprocess and speak MCP over stdin/stdout. That is the entire integration.

### Hosted / remote (HTTP transport)

For team-shared instances or agents that can't spawn a local subprocess:

```bash
uvx gnomon-mcp --transport streamable-http --host 0.0.0.0 --port 8000
# also supported: --transport sse
```

Then point your MCP client at `http://<host>:8000/mcp` (or `/sse` for the SSE transport).

## Tell your agent to actually use it

The single biggest reason agents still guess after you wire in a tool is that they were never told to reach for it. Paste this (or a variant) into your agent's system prompt:

```text
You have access to gnomon, a deterministic MCP tool server for dates and math.
Use it instead of computing in your head — your arithmetic and date estimates
are unreliable, gnomon's are not.

- `now` (optional tz): the current moment. Call this whenever a request
  depends on "today", "right now", "this week", etc. Your training cutoff
  is not today.
- `calendar(ops)`: batch dispatcher for date math. Use for time-until,
  time-since, elapsed time, weekday lookup, business-day counts, adding
  months/years to dates, formatting, and natural-language date parsing
  ("next thursday", "in 3 hours").
- `calc(expressions)`: batch Python expression evaluator with math, stats,
  and common builtins pre-loaded. Use for any arithmetic past trivial
  mental math, including percentages, sums, averages, and table-row math.
- `calc_convert(value, from_unit, to_unit)`: unit conversion (meters/feet,
  kg/lb, °C/°F, bytes/MiB, etc.). Never eyeball these.

Both batch tools take a list and return a list in order — prefer one batched
call over many small ones.
```

## Development

```bash
git clone https://github.com/lihtness/gnomon-mcp
cd gnomon-mcp
pip install -e ".[dev]"
pytest
```

## License

MIT
