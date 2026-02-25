"""Tiny helper for driving `anymoment` CLI and parsing JSON output.

This stays portable: expects `anymoment` on PATH (or `ANYMOMENT_BIN`).
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Optional, Sequence


@dataclass
class RunResult:
    ok: bool
    code: int
    stdout: str
    stderr: str
    json: Optional[Any] = None


def choose_anymoment_bin() -> str:
    return os.environ.get("ANYMOMENT_BIN") or "anymoment"


def run_anymoment(args: Sequence[str], *, timeout_s: int = 120) -> RunResult:
    cmd = [choose_anymoment_bin(), *args]
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    p = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )

    res = RunResult(ok=p.returncode == 0, code=p.returncode, stdout=p.stdout or "", stderr=p.stderr or "")

    out = (p.stdout or "").strip()
    if out.startswith("{") or out.startswith("["):
        try:
            res.json = json.loads(out)
        except Exception:
            pass

    return res


def run_raw(args: Sequence[str], **kw: Any) -> RunResult:
    a = list(args)
    if "--raw" not in a:
        a.append("--raw")
    return run_anymoment(a, **kw)


def run_agenda(start: str, end: str, calendar_ids: Optional[Sequence[str]] = None, use_cache: bool = True, include_webhooks: bool = False, raw: bool = True, **kw: Any) -> RunResult:
    args = ["agenda", "list", "--start", start, "--end", end]
    if calendar_ids:
        args += ["--calendar", ",".join(str(c) for c in calendar_ids)]
    if not use_cache:
        args.append("--no-cache")
    if include_webhooks:
        args.append("--webhooks")
    if raw and "--raw" not in args:
        args.append("--raw")
    return run_anymoment(args, **kw)


def run_agenda_search(query: str, start: Optional[str] = None, end: Optional[str] = None, calendar_ids: Optional[Sequence[str]] = None, is_active: Optional[bool] = None, limit: Optional[int] = None, offset: Optional[int] = None, include_instances: bool = True, raw: bool = True, **kw: Any) -> RunResult:
    args = ["agenda", "search", query]
    if start:
        args += ["--start", start]
    if end:
        args += ["--end", end]
    if calendar_ids:
        args += ["--calendar", ",".join(str(c) for c in calendar_ids)]
    if is_active is not None:
        args += ["--active"] if is_active else ["--inactive"]
    if limit is not None:
        args += ["--limit", str(limit)]
    if offset is not None:
        args += ["--offset", str(offset)]
    if not include_instances:
        args += ["--no-instances"]
    if raw and "--raw" not in args:
        args.append("--raw")
    return run_anymoment(args, **kw)


def run_create(text: str, calendar: Optional[str] = None, context: Optional[str] = None, timezone: Optional[str] = None, model: str = "high", raw: bool = True, **kw: Any) -> RunResult:
    """Run `anymoment create` (extract + create). Calendar can be name or ID."""
    args = ["create", text]
    if calendar is not None:
        args += ["--calendar", calendar]
    if context is not None:
        args += ["--context", context]
    if timezone is not None:
        args += ["--timezone", timezone]
    if model != "high":
        args += ["--model", model]
    if raw and "--raw" not in args:
        args.append("--raw")
    return run_anymoment(args, **kw)


def run_update(event_id: str, when: Optional[str] = None, title: Optional[str] = None, description: Optional[str] = None, timezone: Optional[str] = None, model: str = "high", raw: bool = True, **kw: Any) -> RunResult:
    """Run `anymoment update`. At least one of when, title, description required."""
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
    if raw and "--raw" not in args:
        args.append("--raw")
    return run_anymoment(args, **kw)
