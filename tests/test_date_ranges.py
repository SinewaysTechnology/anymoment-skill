"""Current behavior of scripts/date_ranges.py."""

from __future__ import annotations

from datetime import datetime

import json

import pytest

import date_ranges


class FrozenDateTime(datetime):
    """Wednesday 14 October 2026, 15:30, in whatever timezone the caller passes."""

    @classmethod
    def now(cls, tz=None):
        base = datetime(2026, 10, 14, 15, 30, 0)
        if tz is not None:
            return base.replace(tzinfo=tz)
        return base


@pytest.fixture
def frozen_now(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(date_ranges, "datetime", FrozenDateTime)


def test_next_week_is_monday_through_sunday(frozen_now):
    start, end = date_ranges.next_week_range("Europe/Madrid")
    assert start == "2026-10-19T00:00:00+02:00"
    # 25 October 2026 is the CET changeover, so the Sunday end is +01:00.
    assert end == "2026-10-25T23:59:59+01:00"


def test_default_main_is_today(frozen_now, capsys: pytest.CaptureFixture[str]):
    date_ranges.main(["--tz", "Europe/Madrid"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["start"] == "2026-10-14T00:00:00+02:00"
    assert payload["end"] == "2026-10-14T23:59:59+02:00"


def test_days_back_only_ends_at_now(frozen_now):
    start, end = date_ranges.relative_range(4, 0, 0, 0, 0, 0, "Europe/Madrid")
    assert start == "2026-10-10T00:00:00+02:00"
    assert end == "2026-10-14T15:30:00+02:00"


def test_days_forward_only_starts_at_now(frozen_now):
    start, end = date_ranges.relative_range(0, 2, 0, 0, 0, 0, "Europe/Madrid")
    assert start == "2026-10-14T15:30:00+02:00"
    assert end == "2026-10-16T23:59:59+02:00"


def test_back_and_forward_use_full_days(frozen_now):
    start, end = date_ranges.relative_range(1, 1, 0, 0, 0, 0, "Europe/Madrid")
    assert start == "2026-10-13T00:00:00+02:00"
    assert end == "2026-10-15T23:59:59+02:00"


def test_named_range_from_main(frozen_now, capsys: pytest.CaptureFixture[str]):
    date_ranges.main(["next-week", "--tz", "Europe/Madrid"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["start"].startswith("2026-10-19T00:00:00")
    assert payload["end"].startswith("2026-10-25T23:59:59")


def test_unknown_timezone_raises():
    with pytest.raises(Exception):
        date_ranges.next_week_range("Not/AZone")
