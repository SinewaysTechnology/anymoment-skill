"""Script tests against mocked CLI output of the real HTTP bodies.

`anymoment_api` shells out to the CLI. These tests point ANYMOMENT_BIN at a
fake executable that prints fixture files captured from the API shapes, so
nothing talks to the network.
"""

from __future__ import annotations

import json

import pytest

import anymoment_api
from conftest import FIXTURES, FakeCli


def _body(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_default_binary_name(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ANYMOMENT_BIN", raising=False)
    assert anymoment_api.choose_anymoment_bin() == "anymoment"


def test_plain_stdout_is_not_json(cli: FakeCli, tmp_path):
    plain = tmp_path / "plain.txt"
    plain.write_text("Found 2 event(s)\n", encoding="utf-8")
    cli.install(stdout=plain)
    result = anymoment_api.run_anymoment(["agenda", "list"])
    assert result.ok is True
    assert result.json is None
    assert result.stdout.startswith("Found 2")


def test_utf8_env_is_set_on_the_child(cli: FakeCli, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("PYTHONUTF8", raising=False)
    monkeypatch.delenv("PYTHONIOENCODING", raising=False)
    cli.install()
    anymoment_api.run_anymoment(["--version"])
    env = cli.child_env()
    assert env["PYTHONUTF8"] == "1"
    assert env["PYTHONIOENCODING"] == "utf-8"


def test_run_agenda_builds_argv_and_parses_the_agenda_object(cli: FakeCli):
    cli.install(stdout=FIXTURES / "agenda_200.json")
    result = anymoment_api.run_agenda(
        "2026-10-12T00:00:00+02:00",
        "2026-10-18T23:59:59+02:00",
        calendar_ids=["cal-1", "cal-2"],
        use_cache=False,
        include_webhooks=True,
    )
    assert result.ok is True
    assert result.json == _body("agenda_200.json")
    assert isinstance(result.json, dict)
    assert cli.argv() == [
        "agenda",
        "list",
        "--start",
        "2026-10-12T00:00:00+02:00",
        "--end",
        "2026-10-18T23:59:59+02:00",
        "--calendar",
        "cal-1,cal-2",
        "--no-cache",
        "--webhooks",
        "--json",
        "--fields",
        "events,failures",
    ]
    assert not any("admin" in token for token in cli.argv())


def test_parsed_agenda_keeps_failures_in_the_raw_object(cli: FakeCli):
    cli.install(stdout=FIXTURES / "agenda_200.json")
    result = anymoment_api.run_agenda("2026-10-14T00:00:00Z", "2026-10-14T23:59:59Z")
    assert result.json["failures"][0]["event_name"] == "Imported review"
    assert result.json["events"][0]["event"]["display_name"] == "Standup"


def test_run_agenda_search_argv(cli: FakeCli, tmp_path):
    payload = tmp_path / "search.json"
    payload.write_text("[]\n", encoding="utf-8")
    cli.install(stdout=payload)
    result = anymoment_api.run_agenda_search(
        "standup",
        start="2026-10-12T00:00:00Z",
        end="2026-10-18T23:59:59Z",
        is_active=False,
        limit=10,
        include_instances=False,
    )
    assert result.ok is True
    assert result.json == []
    assert cli.argv() == [
        "agenda",
        "search",
        "standup",
        "--start",
        "2026-10-12T00:00:00Z",
        "--end",
        "2026-10-18T23:59:59Z",
        "--inactive",
        "--limit",
        "10",
        "--no-instances",
        "--json",
    ]


def test_run_create_omits_default_model(cli: FakeCli, tmp_path):
    payload = tmp_path / "create.json"
    payload.write_text('{"id": "ev-1"}\n', encoding="utf-8")
    cli.install(stdout=payload)
    result = anymoment_api.run_create("Standup every weekday at 9am", calendar="Work")
    assert result.json == {"id": "ev-1"}
    assert "--model" not in cli.argv()
    assert cli.argv()[:2] == ["create", "Standup every weekday at 9am"]
    assert "--calendar" in cli.argv() and "Work" in cli.argv()
    assert cli.argv()[-1] == "--json"


def test_run_create_passes_non_default_model(cli: FakeCli, tmp_path):
    payload = tmp_path / "create.json"
    payload.write_text("{}\n", encoding="utf-8")
    cli.install(stdout=payload)
    anymoment_api.run_create("Dentist Friday 10am", model="low", as_json=False)
    assert "--model" in cli.argv()
    assert "low" in cli.argv()
    assert "--json" not in cli.argv()


def test_run_update_argv(cli: FakeCli, tmp_path):
    payload = tmp_path / "update.json"
    payload.write_text("{}\n", encoding="utf-8")
    cli.install(stdout=payload)
    anymoment_api.run_update("abc-123", when="Every Tuesday at 11am", title="New name")
    assert cli.argv()[:2] == ["update", "abc-123"]
    assert "--when" in cli.argv()
    assert "--title" in cli.argv()
    assert "--json" in cli.argv()


def test_error_json_on_stdout_is_parsed_and_not_ok(cli: FakeCli):
    body = _body("error_502.json")
    cli.install(stdout=FIXTURES / "error_502.json", code=1)
    result = anymoment_api.run_anymoment(["agenda", "list", "--json"])
    assert result.ok is False
    assert result.code == 1
    assert result.json == body
    assert result.user_message == body["user_message"]
    assert result.next_step == body["next_step"]


def test_run_agenda_exposes_events_and_failures(cli: FakeCli):
    body = _body("agenda_200.json")
    cli.install(stdout=FIXTURES / "agenda_200.json")
    result = anymoment_api.run_agenda("2026-10-12T00:00:00+02:00", "2026-10-18T23:59:59+02:00")
    assert result.ok is True
    assert result.events == body["events"]
    assert result.failures == body["failures"]
    assert result.failures


def test_error_body_surfaces_user_message_and_next_step(cli: FakeCli):
    body = _body("error_502.json")
    cli.install(stdout=FIXTURES / "error_502.json", code=1)
    result = anymoment_api.run_anymoment(["agenda", "list"])
    assert result.user_message == body["user_message"]
    assert result.next_step == body["next_step"]


def test_caldav_error_surfaces_user_message_and_next_step(cli: FakeCli):
    detail = _body("error_caldav.json")["detail"]
    cli.install(stdout=FIXTURES / "error_caldav.json", code=1)
    result = anymoment_api.run_anymoment(["calendars", "list"])
    assert result.user_message == detail["message"]
    assert result.next_step == detail["next_step"]


def test_rate_limit_body_surfaces_user_message_and_retry_after(cli: FakeCli):
    body = _body("error_429.json")
    cli.install(stdout=FIXTURES / "error_429.json", code=1)
    result = anymoment_api.run_anymoment(["agenda", "list"])
    assert result.user_message == body["user_message"]
    assert result.retry_after == body["retry_after_seconds"]


def test_stderr_error_object_overrides_stdout(cli: FakeCli, tmp_path):
    stdout = tmp_path / "out.json"
    stderr = tmp_path / "err.json"
    stdout.write_text('{"events": [], "failures": []}\n', encoding="utf-8")
    stderr.write_text(
        json.dumps(
            {
                "error": {
                    "code": "rate_limited",
                    "user_message": "Wait before trying again.",
                    "next_step": "Retry after the delay.",
                    "retry_after": 30,
                }
            }
        ),
        encoding="utf-8",
    )
    cli.install(stdout=stdout, stderr=stderr, code=anymoment_api.EXIT_RATE_LIMIT)
    result = anymoment_api.run_anymoment(["today", "--json"])
    assert result.ok is False
    assert result.code == anymoment_api.EXIT_RATE_LIMIT
    assert result.user_message == "Wait before trying again."
    assert result.next_step == "Retry after the delay."
    assert result.retry_after == 30


def test_success_message_is_not_an_error(cli: FakeCli, tmp_path):
    payload = tmp_path / "delete.json"
    payload.write_text(
        json.dumps(
            {
                "message": "Event deleted",
                "sync_warnings": [
                    {"user_message": "Google copy was not updated.", "next_step": "Reconnect that account."}
                ],
            }
        ),
        encoding="utf-8",
    )
    cli.install(stdout=payload)
    result = anymoment_api.run_anymoment(["rm", "abc-123", "--yes", "--json"])
    assert result.ok is True
    assert result.user_message is None
    assert result.sync_warnings[0]["next_step"] == "Reconnect that account."


def test_run_window_uses_a_relative_phrase(cli: FakeCli):
    cli.install(stdout=FIXTURES / "agenda_200.json")
    result = anymoment_api.run_window("tomorrow", calendar="Work")
    assert result.events
    assert result.failures
    assert cli.argv() == [
        "agenda",
        "tomorrow",
        "--calendar",
        "Work",
        "--json",
        "--fields",
        "events,failures",
    ]


def test_read_only_external_event():
    events = _body("agenda_200.json")["events"]
    assert anymoment_api.event_is_read_only(events[0]["event"]) is False
    assert anymoment_api.event_is_read_only(events[1]["event"]) is True
    assert anymoment_api.event_is_read_only({"google_origin": True}) is True
