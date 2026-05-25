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


# ---- standalone: rich "right now" snapshot ----

_MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"]


def now(tz: Optional[str] = None) -> dict[str, Any]:
    """Return a rich snapshot of the current moment.

    One call gets you everything: ISO string, date, time, weekday, day-of-year,
    week-of-year (ISO), quarter, US federal fiscal year, hour/minute/second,
    unix timestamp, timezone, weekend flag.

    tz: IANA timezone (e.g. 'America/Los_Angeles'). Defaults to UTC.
    """
    dt = datetime.now(_resolve_tz(tz))
    iso_cal = dt.isocalendar()
    weekday_num = dt.weekday()
    return {
        "iso": dt.isoformat(),
        "date": dt.date().isoformat(),
        "time": dt.time().isoformat(timespec="seconds"),
        "unix": int(dt.timestamp()),
        "tz": tz or "UTC",
        "year": dt.year,
        "month": dt.month,
        "month_name": _MONTH_NAMES[dt.month],
        "day": dt.day,
        "weekday": _WEEKDAY_NAMES[weekday_num],
        "weekday_num": weekday_num,  # 0=Monday
        "day_of_year": dt.timetuple().tm_yday,
        "week_of_year": iso_cal.week,  # ISO week
        "quarter": (dt.month - 1) // 3 + 1,
        "fiscal_year_us_gov": dt.year + (1 if dt.month >= 10 else 0),
        "hour": dt.hour,
        "minute": dt.minute,
        "second": dt.second,
        "is_weekend": weekday_num >= 5,
    }


# ---- batch operations (each returns a scalar) ----

def _diff_seconds_to_unit(seconds: float, unit: str) -> float:
    if unit not in _UNITS_DELTA:
        raise ValueError(f"unit must be one of {sorted(_UNITS_DELTA)}")
    return {
        "seconds": seconds,
        "minutes": seconds / 60,
        "hours": seconds / 3600,
        "days": seconds / 86400,
        "weeks": seconds / 604800,
    }[unit]


def _diff(start: str, end: str, unit: str = "days") -> float:
    seconds = (_parse_date(end) - _parse_date(start)).total_seconds()
    return _diff_seconds_to_unit(seconds, unit)


def _until(target: str, unit: str = "days", tz: Optional[str] = None) -> float:
    """Time left from now to target. Positive if target is in the future."""
    target_dt = _parse_date(target)
    if target_dt.tzinfo is None:
        target_dt = target_dt.replace(tzinfo=_resolve_tz(tz))
    seconds = (target_dt - datetime.now(_resolve_tz(tz))).total_seconds()
    return _diff_seconds_to_unit(seconds, unit)


def _since(source: str, unit: str = "days", tz: Optional[str] = None) -> float:
    """Time elapsed from source to now. Positive if source is in the past."""
    source_dt = _parse_date(source)
    if source_dt.tzinfo is None:
        source_dt = source_dt.replace(tzinfo=_resolve_tz(tz))
    seconds = (datetime.now(_resolve_tz(tz)) - source_dt).total_seconds()
    return _diff_seconds_to_unit(seconds, unit)


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
    "diff": _diff,
    "until": _until,
    "since": _since,
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
      {"op": "diff", "start": "2026-01-01", "end": "2026-12-31", "unit": "days"}
          -> end - start as float in the unit (seconds|minutes|hours|days|weeks)
      {"op": "until", "target": "2026-12-31", "unit": "days", "tz": "UTC"}
          -> time left from now to target (positive if future)
      {"op": "since", "source": "2026-01-01", "unit": "days", "tz": "UTC"}
          -> time elapsed from source to now (positive if past)
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

    For "what is right now" use the standalone `now()` tool — it returns
    a rich dict (year, month, weekday, quarter, week_of_year, etc.) in one call.

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
