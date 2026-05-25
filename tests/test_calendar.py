from datetime import datetime

import pytest

from gnomon_mcp.tools.calendar_tools import calendar


class TestCalendarSingleOps:
    def test_now_utc_default(self):
        [iso] = calendar([{"op": "now"}])
        parsed = datetime.fromisoformat(iso)
        assert parsed.utcoffset().total_seconds() == 0

    def test_now_named_tz(self):
        [iso] = calendar([{"op": "now", "tz": "America/Los_Angeles"}])
        assert datetime.fromisoformat(iso).tzinfo is not None

    def test_diff_days(self):
        assert calendar([{"op": "diff", "start": "2026-01-01", "end": "2026-01-08", "unit": "days"}]) == [7.0]

    def test_diff_hours(self):
        assert calendar([
            {"op": "diff", "start": "2026-01-01T00:00:00", "end": "2026-01-01T06:00:00", "unit": "hours"}
        ]) == [6.0]

    def test_add_days(self):
        [iso] = calendar([{"op": "add", "date": "2026-01-01", "n": 30, "unit": "days"}])
        assert iso.startswith("2026-01-31")

    def test_add_months_calendar_aware(self):
        [iso] = calendar([{"op": "add", "date": "2026-01-31", "n": 1, "unit": "months"}])
        assert iso.startswith("2026-02-28")

    def test_weekday(self):
        # 2026-05-25 is a Monday
        assert calendar([{"op": "weekday", "date": "2026-05-25"}]) == ["Monday"]

    def test_business_days_full_week(self):
        assert calendar([{"op": "business_days", "start": "2026-05-25", "end": "2026-06-01"}]) == [5]

    def test_business_days_reversed_negative(self):
        assert calendar([{"op": "business_days", "start": "2026-06-01", "end": "2026-05-25"}]) == [-5]

    def test_parse_explicit(self):
        [iso] = calendar([{"op": "parse", "natural": "2026-12-25"}])
        assert iso.startswith("2026-12-25")

    def test_format(self):
        [s] = calendar([{"op": "format", "date": "2026-05-25", "fmt": "%A"}])
        assert s == "Monday"


class TestCalendarBatch:
    def test_heterogeneous_batch_preserves_order(self):
        results = calendar([
            {"op": "weekday", "date": "2026-05-25"},
            {"op": "diff", "start": "2026-01-01", "end": "2026-12-31", "unit": "days"},
            {"op": "add", "date": "2026-05-25", "n": 7, "unit": "days"},
            {"op": "format", "date": "2026-05-25", "fmt": "%Y-%m"},
        ])
        assert results[0] == "Monday"
        assert results[1] == 364.0
        assert results[2].startswith("2026-06-01")
        assert results[3] == "2026-05"

    def test_table_row_style(self):
        # Simulate computing weekday for many rows in one call
        dates = ["2026-05-25", "2026-05-26", "2026-05-27", "2026-05-28"]
        ops = [{"op": "weekday", "date": d} for d in dates]
        assert calendar(ops) == ["Monday", "Tuesday", "Wednesday", "Thursday"]

    def test_single_dict_tolerated(self):
        assert calendar({"op": "weekday", "date": "2026-05-25"}) == ["Monday"]


class TestCalendarErrors:
    def test_missing_op_key(self):
        with pytest.raises(ValueError, match="op 0"):
            calendar([{"date": "2026-05-25"}])

    def test_unknown_op(self):
        with pytest.raises(ValueError, match="unknown op"):
            calendar([{"op": "vibe", "date": "2026-05-25"}])

    def test_error_reports_index(self):
        with pytest.raises(ValueError, match="op 1"):
            calendar([
                {"op": "weekday", "date": "2026-05-25"},
                {"op": "diff", "start": "2026-01-01", "end": "2026-12-31", "unit": "fortnights"},
            ])

    def test_bad_args_reports_op(self):
        with pytest.raises(ValueError, match="bad arguments"):
            calendar([{"op": "weekday"}])  # missing required `date`
