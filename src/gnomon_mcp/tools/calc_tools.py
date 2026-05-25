"""Calculator tools — flexible Python-expression evaluation + unit conversion."""
from __future__ import annotations

import math
import statistics
from typing import Any, Sequence

from pint import UnitRegistry

_ureg = UnitRegistry()


def _build_namespace() -> dict[str, Any]:
    """Namespace exposed to calc expressions.

    Pre-loads math, statistics, and the calc-relevant builtins so expressions
    like `sqrt(16)`, `mean([1,2,3])`, `sum(range(10))` work out of the box.
    """
    ns: dict[str, Any] = {}
    # math module (sqrt, sin, cos, log, exp, pi, e, tau, inf, nan, ...)
    for name in dir(math):
        if not name.startswith("_"):
            ns[name] = getattr(math, name)
    # common stats
    ns["mean"] = statistics.fmean
    ns["median"] = statistics.median
    ns["mode"] = statistics.mode
    ns["stdev"] = lambda xs: statistics.stdev(xs) if len(list(xs)) > 1 else 0.0
    ns["variance"] = lambda xs: statistics.variance(xs) if len(list(xs)) > 1 else 0.0
    # calc-relevant builtins
    for name in ("abs", "round", "min", "max", "sum", "len", "pow",
                 "divmod", "int", "float", "bool", "list", "tuple",
                 "range", "sorted", "reversed", "zip", "enumerate", "map", "filter"):
        ns[name] = __builtins__[name] if isinstance(__builtins__, dict) else getattr(__builtins__, name)
    return ns


_NAMESPACE = _build_namespace()


def calc(expressions: Sequence[str]) -> list[Any]:
    """Eval Python expressions -> list. Pre-loaded: math, statistics (mean/median/stdev/variance), abs/round/min/max/sum/range/sorted."""
    if isinstance(expressions, str):
        # tolerate a single string for ergonomics
        expressions = [expressions]
    results: list[Any] = []
    for i, expr in enumerate(expressions):
        try:
            results.append(eval(expr, {"__builtins__": {}}, _NAMESPACE))
        except Exception as e:
            raise ValueError(f"expression {i} ({expr!r}) failed: {e}") from e
    return results


def calc_convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert value between units (Pint). E.g. ('meter','foot'), ('kg','lb'), ('degC','degF')."""
    try:
        quantity = _ureg.Quantity(value, from_unit).to(to_unit)
    except Exception as e:
        raise ValueError(f"conversion failed: {e}") from e
    return float(quantity.magnitude)
