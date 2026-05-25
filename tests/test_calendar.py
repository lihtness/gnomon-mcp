from datetime import datetime, timedelta, timezone

import pytest

from gnomon_mcp.tools.calendar_tools import calendar, now


class TestNow:
    def test_returns_rich_dict(self):
        snap = now()
        expected_keys = {
            "iso", "date", "time", "unix", "tz",
            "year", "month", "month_name", "day",
            "weekday", "weekday_num", "day_of_year",
            "week_of_year", "quarter", "fiscal_year_us_gov",
            "hour", "minute", "second", "is_weekend",
        }
        assert set(snap.keys()) == expected_keys

    def test_utc_default(self):
        snap = now()
        assert snap["tz"] == "UTC"
        assert datetime.fromisoformat(snap["iso"]).utcoffset().total_seconds() == 0

    def test_named_tz(self):
        snap = now("America/Los_Angeles")
        assert snap["tz"] == "America/Los_Angeles"
        assert datetime.fromisoformat(snap["iso"]).tzinfo is not None

    def test_quarter_derived_from_month(self):
        snap = now()
        assert snap["quarter"] == (snap["month"] - 1) // 3 + 1

    def test_fiscal_year_us_gov(self):
        snap = now()
        expected_fy = snap["year"] + (1 if snap["month"] >= 10 else 0)
        assert snap["fiscal_year_us_gov"] == expected_fy

    def test_weekday_matches_num(self):
        snap = now()
        names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        assert snap["weekday"] == names[snap["weekday_num"]]

    def test_is_weekend_flag(self):
        snap = now()
        assert snap["is_weekend"] == (snap["weekday_num"] >= 5)


class TestCalendarSingleOps:
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


class TestUntilSince:
    def test_until_future(self):
        future = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        [days] = calendar([{"op": "until", "target": future, "unit": "days"}])
        assert 9.9 < days < 10.1

    def test_until_past_is_negative(self):
        past = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        [days] = calendar([{"op": "until", "target": past, "unit": "days"}])
        assert -5.1 < days < -4.9

    def test_since_past(self):
        past = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        [days] = calendar([{"op": "since", "source": past, "unit": "days"}])
        assert 6.9 < days < 7.1

    def test_since_future_is_negative(self):
        future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        [days] = calendar([{"op": "since", "source": future, "unit": "days"}])
        assert -3.1 < days < -2.9

    def test_until_naive_date_treated_as_tz(self):
        # Naive ISO date with tz hint — should not raise
        result = calendar([{"op": "until", "target": "2099-01-01", "unit": "days", "tz": "UTC"}])
        assert result[0] > 0

    def test_until_in_hours(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        [hours] = calendar([{"op": "until", "target": future, "unit": "hours"}])
        assert 11.99 < hours < 12.01

    def test_batch_mix_until_and_since(self):
        future = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        past = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        results = calendar([
            {"op": "until", "target": future, "unit": "days"},
            {"op": "since", "source": past, "unit": "days"},
        ])
        assert results[0] > 0 and results[1] > 0


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
