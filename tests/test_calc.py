import math

import pytest

from gnomon_mcp.tools.calc_tools import calc, calc_convert


class TestCalc:
    def test_arithmetic(self):
        assert calc(["2 + 3 * 4"]) == [14]

    def test_power_and_parens(self):
        assert calc(["(2 + 3) ** 2"]) == [25]

    def test_math_functions(self):
        results = calc(["sqrt(16)", "sin(pi/2)", "log(e)"])
        assert results[0] == 4.0
        assert math.isclose(results[1], 1.0, abs_tol=1e-9)
        assert math.isclose(results[2], 1.0, abs_tol=1e-9)

    def test_stats(self):
        assert calc(["mean([1, 2, 3, 4])"]) == [2.5]
        assert calc(["median([1, 3, 5, 7])"]) == [4.0]

    def test_builtins(self):
        assert calc(["sum(range(101))"]) == [5050]
        assert calc(["sorted([3, 1, 2])"]) == [[1, 2, 3]]

    def test_batch_order_preserved(self):
        results = calc(["1+1", "2+2", "3+3"])
        assert results == [2, 4, 6]

    def test_percent_via_expression(self):
        assert calc(["(25 / 100) * 100"]) == [25.0]

    def test_single_string_tolerated(self):
        assert calc("2 + 2") == [4]

    def test_bad_expression_raises(self):
        with pytest.raises(ValueError):
            calc(["1 +"])

    def test_import_blocked(self):
        # No __builtins__ → no __import__
        with pytest.raises(ValueError):
            calc(["__import__('os')"])


class TestCalcConvert:
    def test_length(self):
        assert math.isclose(calc_convert(1, "meter", "foot"), 3.2808398950131235)

    def test_mass(self):
        assert math.isclose(calc_convert(1, "kilogram", "pound"), 2.2046226218487757)

    def test_temperature(self):
        assert math.isclose(calc_convert(0, "degC", "degF"), 32.0)

    def test_incompatible_raises(self):
        with pytest.raises(ValueError):
            calc_convert(1, "meter", "kilogram")
