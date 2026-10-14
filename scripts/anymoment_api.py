"""Drive the anymoment CLI and read its 2.0 JSON.

Expects `anymoment` on PATH, or `ANYMOMENT_BIN`. `ANYMOMENT_TOKEN` is passed
through for non-interactive auth. Machine output is `--json`. Agenda stdout
is `{events, failures}` (a `v` envelope is fine). Failures stay on the result.
A non-zero exit reads `user_message`, `next_step`, and `retry_after` from
stderr `{"error": {...}}` or from a JSON error body on stdout.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_AUTH = 3
EXIT_NOT_FOUND = 4
EXIT_CONFLICT = 5
EXIT_RATE_LIMIT = 6
EXIT_REMOTE = 7


@dataclass
class RunResult:
    ok: bool
    code: int
    stdout: str
    stderr: str
    json: Optional[Any] = None
    events: list[Any] = field(default_factory=list)
    failures: list[Any] = field(default_factory=list)
    sync_warnings: list[Any] = field(default_factory=list)
    google_export_warnings: list[Any] = field(default_factory=list)
    user_message: Optional[str] = None
    next_step: Optional[str] = None
    retry_after: Optional[int] = None


def choose_anymoment_bin() -> str:
    return os.environ.get("ANYMOMENT_BIN") or "anymoment"


def _loads_json(text: str) -> Any:
    stripped = (text or "").strip()
    if not stripped or stripped[0] not in "{[":
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def _error_source(payload: Any) -> Optional[dict]:
    if not isinstance(payload, dict):
        return None
    nested = payload.get("error")
    if isinstance(nested, dict):
        return nested
    detail = payload.get("detail")
    if isinstance(detail, dict):
        return detail
    keys = ("user_message", "next_step", "retry_after", "retry_after_seconds")
    if any(key in payload for key in keys):
        return payload
    return None


def _apply_error(result: RunResult, source: dict) -> None:
    message = source.get("user_message")
    if not message and source.get("message"):
        message = source["message"]
    if message:
        result.user_message = message
    step = source.get("next_step")
    if step:
        result.next_step = step
    retry = source.get("retry_after")
    if retry is None:
        retry = source.get("retry_after_seconds")
    if retry is not None:
        result.retry_after = retry


def _apply_body(result: RunResult, payload: Any, *, failed: bool) -> None:
    if isinstance(payload, dict):
        if "events" in payload or "failures" in payload:
            result.events = list(payload.get("events") or [])
            result.failures = list(payload.get("failures") or [])
        warnings = payload.get("sync_warnings")
        if isinstance(warnings, list):
            result.sync_warnings = list(warnings)
        export_warnings = payload.get("google_export_warnings")
        if isinstance(export_warnings, list):
            result.google_export_warnings = list(export_warnings)
    if failed:
        source = _error_source(payload)
        if source:
            _apply_error(result, source)


def event_is_read_only(event: Any) -> bool:
    """True for a Google import or a CalDAV event with read_only set."""
    if not isinstance(event, dict):
        return False
    if event.get("google_origin"):
        return True
    origin = event.get("external_origin") or {}
    return bool(isinstance(origin, dict) and origin.get("read_only"))


def run_anymoment(args: Sequence[str], *, timeout_s: int = 120) -> RunResult:
    cmd = [choose_anymoment_bin(), *args]
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    completed = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    result = RunResult(
        ok=completed.returncode == EXIT_OK,
        code=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )
    stdout_payload = _loads_json(result.stdout)
    if stdout_payload is not None:
        result.json = stdout_payload
        _apply_body(result, stdout_payload, failed=result.code != EXIT_OK)

    stderr_payload = _loads_json(result.stderr)
    if stderr_payload is not None and result.code != EXIT_OK:
        _apply_body(result, stderr_payload, failed=True)
    return result


def _json_flags(fields: Optional[str], as_json: bool) -> list[str]:
    if not as_json:
        return []
    flags = ["--json"]
    if fields:
        flags += ["--fields", fields]
    return flags


def run_json(args: Sequence[str], fields: Optional[str] = None, **kw: Any) -> RunResult:
    command = list(args)
    if "--json" not in command and "--jsonl" not in command:
        command += _json_flags(fields, True)
    return run_anymoment(command, **kw)


def run_agenda(
    start: str,
    end: str,
    calendar_ids: Optional[Sequence[str]] = None,
    use_cache: bool = True,
    include_webhooks: bool = False,
    fields: Optional[str] = "events,failures",
    as_json: bool = True,
    **kw: Any,
) -> RunResult:
    args = ["agenda", "list", "--start", start, "--end", end]
    if calendar_ids:
        args += ["--calendar", ",".join(str(calendar) for calendar in calendar_ids)]
    if not use_cache:
        args.append("--no-cache")
    if include_webhooks:
        args.append("--webhooks")
    args += _json_flags(fields, as_json)
    return run_anymoment(args, **kw)


def run_window(
    window: str = "today",
    calendar: Optional[str] = None,
    fields: Optional[str] = "events,failures",
    as_json: bool = True,
    **kw: Any,
) -> RunResult:
    """Natural window: today, tomorrow, this week, next week, next fri."""
    args = ["agenda", window]
    if calendar is not None:
        args += ["--calendar", calendar]
    args += _json_flags(fields, as_json)
    return run_anymoment(args, **kw)


def run_agenda_search(
    query: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    calendar_ids: Optional[Sequence[str]] = None,
    is_active: Optional[bool] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    include_instances: bool = True,
    fields: Optional[str] = None,
    as_json: bool = True,
    **kw: Any,
) -> RunResult:
    args = ["agenda", "search", query]
    if start:
        args += ["--start", start]
    if end:
        args += ["--end", end]
    if calendar_ids:
        args += ["--calendar", ",".join(str(calendar) for calendar in calendar_ids)]
    if is_active is not None:
        args += ["--active"] if is_active else ["--inactive"]
    if limit is not None:
        args += ["--limit", str(limit)]
    if offset is not None:
        args += ["--offset", str(offset)]
    if not include_instances:
        args += ["--no-instances"]
    args += _json_flags(fields, as_json)
    return run_anymoment(args, **kw)


def run_create(
    text: str,
    calendar: Optional[str] = None,
    context: Optional[str] = None,
    timezone: Optional[str] = None,
    model: str = "high",
    fields: Optional[str] = None,
    as_json: bool = True,
    dry_run: bool = False,
    **kw: Any,
) -> RunResult:
    """Run `anymoment create`. Pass dry_run=True before a real create."""
    args = ["create", text]
    if calendar is not None:
        args += ["--calendar", calendar]
    if context is not None:
        args += ["--context", context]
    if timezone is not None:
        args += ["--timezone", timezone]
    if model != "high":
        args += ["--model", model]
    if dry_run:
        args.append("--dry-run")
    args += _json_flags(fields, as_json)
    return run_anymoment(args, **kw)


def run_update(
    event_id: str,
    when: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    timezone: Optional[str] = None,
    model: str = "high",
    fields: Optional[str] = None,
    as_json: bool = True,
    dry_run: bool = False,
    yes: bool = False,
    **kw: Any,
) -> RunResult:
    """Run `anymoment update`. At least one of when, title, description is required."""
    args = ["update", event_id]
    if when is not None:
        args += ["--when", when]
    if title is not None:
        args += ["--title", title]
    if description is not None:
        args += ["--description", description]
    if timezone is not None:
        args += ["--timezone", timezone]
    if model != "high":
        args += ["--model", model]
    if dry_run:
        args.append("--dry-run")
    if yes:
        args.append("--yes")
    args += _json_flags(fields, as_json)
    return run_anymoment(args, **kw)
