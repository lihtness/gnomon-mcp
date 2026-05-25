"""Calendar tools — batch dispatcher over date/time operations.

Designed for table-row use: one tool call evaluates many heterogeneous
operations (diff one row, weekday another, parse a third, ...).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence
from zoneinfo import ZoneInfo

import dateparser
from dateutil import parser as dtparser
from dateutil.relativedelta import relativedelta

_WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_UNITS_DELTA = {"seconds", "minutes", "hours", "days", "weeks"}
_UNITS_RELATIVE = {"months", "years"}


def _resolve_tz(tz: Optional[str]) -> timezone | ZoneInfo:
    if tz is None or tz.upper() == "UTC":
        return timezone.utc
    return ZoneInfo(tz)


def _parse_date(s: str) -> datetime:
    return dtparser.isoparse(s) if "T" in s or " " in s else dtparser.parse(s)


# ---- individual operations (also usable directly) ----

def _now(tz: Optional[str] = None) -> str:
    return datetime.now(_resolve_tz(tz)).isoformat()


def _diff(start: str, end: str, unit: str = "days") -> float:
    if unit not in _UNITS_DELTA:
        raise ValueError(f"unit must be one of {sorted(_UNITS_DELTA)}")
    seconds = (_parse_date(end) - _parse_date(start)).total_seconds()
    return {
        "seconds": seconds,
        "minutes": seconds / 60,
        "hours": seconds / 3600,
        "days": seconds / 86400,
        "weeks": seconds / 604800,
    }[unit]


def _add(date: str, n: int, unit: str = "days") -> str:
    base = _parse_date(date)
    if unit in _UNITS_DELTA:
        result = base + timedelta(**{unit: n})
    elif unit in _UNITS_RELATIVE:
        result = base + relativedelta(**{unit: n})
    else:
        raise ValueError(f"unit must be one of {sorted(_UNITS_DELTA | _UNITS_RELATIVE)}")
    return result.isoformat()


def _weekday(date: str) -> str:
    return _WEEKDAY_NAMES[_parse_date(date).weekday()]


def _business_days(start: str, end: str) -> int:
    s = _parse_date(start).date()
    e = _parse_date(end).date()
    if e < s:
        return -_business_days(end, start)
    days = (e - s).days
    full_weeks, remainder = divmod(days, 7)
    count = full_weeks * 5
    start_wd = s.weekday()
    for i in range(remainder):
        if (start_wd + i) % 7 < 5:
            count += 1
    return count


def _parse_op(natural: str, tz: Optional[str] = None) -> str:
    settings: dict[str, Any] = {"RETURN_AS_TIMEZONE_AWARE": True}
    if tz:
        settings["TIMEZONE"] = tz
        settings["TO_TIMEZONE"] = tz
    parsed = dateparser.parse(natural, settings=settings)
    if parsed is None:
        raise ValueError(f"could not parse: {natural!r}")
    return parsed.isoformat()


def _format(date: str, fmt: str) -> str:
    return _parse_date(date).strftime(fmt)


# ---- dispatch ----

_OPS = {
    "now": _now,
    "diff": _diff,
    "add": _add,
    "weekday": _weekday,
    "business_days": _business_days,
    "parse": _parse_op,
    "format": _format,
}


def calendar(ops: Sequence[dict]) -> list[Any]:
    """Execute a batch of calendar operations and return results in order.

    Each item is a dict with an "op" key plus op-specific parameters.
    Designed for table-row workloads: many rows, one tool call.

    Operations:
      {"op": "now", "tz": "America/Los_Angeles"}
          -> current ISO datetime in tz (default UTC)
      {"op": "diff", "start": "2026-01-01", "end": "2026-12-31", "unit": "days"}
          -> end - start as float in the unit (seconds|minutes|hours|days|weeks)
      {"op": "add", "date": "2026-05-25", "n": 30, "unit": "days"}
          -> ISO of date + n units (units: seconds..weeks, plus months/years)
      {"op": "weekday", "date": "2026-05-25"}
          -> "Monday".."Sunday"
      {"op": "business_days", "start": "2026-05-01", "end": "2026-06-01"}
          -> count of Mon-Fri days (start inclusive, end exclusive)
      {"op": "parse", "natural": "next thursday", "tz": "America/Los_Angeles"}
          -> ISO datetime parsed from natural language
      {"op": "format", "date": "2026-05-25", "fmt": "%A, %B %d %Y"}
          -> strftime-formatted string

    Errors in any item raise immediately with the index and op for debugging.
    """
    if isinstance(ops, dict):
        ops = [ops]
    results: list[Any] = []
    for i, item in enumerate(ops):
        if not isinstance(item, dict) or "op" not in item:
            raise ValueError(f"op {i}: must be a dict with an 'op' key, got {item!r}")
        op_name = item["op"]
        if op_name not in _OPS:
            raise ValueError(f"op {i}: unknown op {op_name!r}. valid: {sorted(_OPS)}")
        kwargs = {k: v for k, v in item.items() if k != "op"}
        try:
            results.append(_OPS[op_name](**kwargs))
        except TypeError as e:
            raise ValueError(f"op {i} ({op_name}): bad arguments — {e}") from e
        except Exception as e:
            raise ValueError(f"op {i} ({op_name}) failed: {e}") from e
    return results
