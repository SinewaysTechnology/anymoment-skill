"""The HTTP fixtures match the public API shapes the skill has to handle.

Agenda: AdvancedEventInstanceBatchResponse {events, failures}.
Failures: EventInstanceFailure.
Errors: top-level user_message/next_step (and the 429 retry body), plus the
CalDAV detail object {code, message, next_step, ...}.
"""

from __future__ import annotations

import json

from conftest import FIXTURES

import lint_skill


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_agenda_fixture_is_events_and_failures():
    body = _load("agenda_200.json")
    assert set(body) == {"events", "failures"}
    assert body["events"]
    assert body["failures"]

    item = body["events"][0]
    assert set(item) == {"event", "instances"}
    event = item["event"]
    required = {
        "id",
        "name",
        "is_active",
        "created_at",
        "updated_at",
        "components",
        "webhooks",
        "display_name",
    }
    assert required <= set(event)
    assert "google_origin" in event
    assert "external_origin" in event
    assert "sync_warnings" in event
    instance = item["instances"][0]
    assert {"start", "end", "is_all_day"} <= set(instance)

    failure = body["failures"][0]
    assert {"event_id", "event_name", "message", "reason", "is_google_synced"} <= set(failure)


def test_agenda_fixture_includes_a_read_only_external_event():
    events = _load("agenda_200.json")["events"]
    read_only = [
        item for item in events if (item["event"].get("external_origin") or {}).get("read_only")
    ]
    assert read_only


def test_error_502_is_top_level_user_message_and_next_step():
    body = _load("error_502.json")
    assert set(body) == {"user_message", "next_step"}
    assert body["user_message"]
    assert body["next_step"]


def test_error_429_carries_retry_after_and_user_message():
    body = _load("error_429.json")
    assert set(body) == {"retry_after_seconds", "user_message"}
    assert body["retry_after_seconds"] > 0
    assert body["user_message"]


def test_caldav_error_detail_has_message_and_next_step():
    detail = _load("error_caldav.json")["detail"]
    assert {"code", "message", "next_step"} <= set(detail)
    assert detail["code"] == "auth_failed"


def test_fixtures_contain_no_admin_endpoints():
    for path in sorted(FIXTURES.glob("*.json")):
        assert lint_skill.find_admin_endpoints(path.read_text(encoding="utf-8")) == []
