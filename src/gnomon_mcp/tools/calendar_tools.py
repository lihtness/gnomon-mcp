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
    """Current moment as dict (iso, date, weekday, week_of_year, quarter, fiscal_year_us_gov, is_weekend, ...). Optional IANA tz."""
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
    """Batch date ops: [{"op": NAME, ...args}, ...] -> [result, ...]

    diff(start, end, unit)  until(target, unit, tz?)  since(source, unit, tz?)  -> float
    add(date, n, unit) -> ISO    weekday(date) -> name
    business_days(start, end) -> int (Mon-Fri, end exclusive)
    parse(natural, tz?) -> ISO    format(date, fmt) -> str

    unit: seconds|minutes|hours|days|weeks (+ months|years for add).
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
