#!/usr/bin/env python3
"""Check skill example bodies against the live AnyMoment OpenAPI document.

Unauthenticated routes are called for real. Bodies that need a key are
validated against the published schemas and listed, not sent.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "references" / "examples"
OPENAPI_URL = "https://api.anymoment.sineways.tech/openapi.json"
API = "https://api.anymoment.sineways.tech"

# These calls need a real key. This script does not send them.
KEY_CHECKS = (
    "POST /events with references/examples/event_*.json (201, and the stored roll and business_calendar)",
    "GET /events/{id}/instances?start=...&end=...&optimized=true for a business-day event",
    "POST /calendars/{id}/subscriptions with subscription_create.json (201, secret once, paused_reason)",
    "GET /calendars/{id}/subscriptions/{id}/deliveries after an occurrence.due",
    "POST /calendars/{id}/events/{id} with calendar_link.json",
    "am auth status with a real ANYMOMENT_API_KEY (status valid, prefix only)",
    "Confirm am events instances --from/--to is not accepted as start/end",
    "403 for a non-owner webhook create, and subscription_required on a lapsed plan",
)


def _load(url: str, method: str = "GET", body: bytes | None = None, headers: dict | None = None):
    request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
            return response.status, dict(response.headers), payload
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def fetch_openapi() -> dict:
    status, _headers, payload = _load(OPENAPI_URL)
    if status != 200:
        raise SystemExit(f"openapi fetch failed: HTTP {status}")
    return json.loads(payload)


def _resolve(node: Any, root: dict, seen: set[str]) -> Any:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            if ref in seen:
                raise SystemExit(f"cyclic schema ref {ref}")
            resolved = _resolve(_pointer(root, ref), root, seen | {ref})
            siblings = {
                key: _resolve(value, root, seen)
                for key, value in node.items()
                if key != "$ref"
            }
            if isinstance(resolved, dict):
                merged = dict(resolved)
                merged.update(siblings)
                return merged
            return resolved
        return {key: _resolve(value, root, seen) for key, value in node.items()}
    if isinstance(node, list):
        return [_resolve(item, root, seen) for item in node]
    return node


def _pointer(root: dict, ref: str) -> Any:
    if not ref.startswith("#/"):
        raise SystemExit(f"unsupported ref {ref}")
    node: Any = root
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            raise SystemExit(f"missing ref {ref}")
        node = node[part]
    return node


def validator_for(spec: dict, name: str) -> Draft202012Validator:
    schema = spec["components"]["schemas"][name]
    resolved = _resolve(schema, spec, set())
    return Draft202012Validator(resolved, format_checker=Draft202012Validator.FORMAT_CHECKER)


def _print(line: str) -> None:
    print(line)


def validate_examples(spec: dict) -> int:
    manifest = json.loads((EXAMPLES / "manifest.json").read_text(encoding="utf-8"))
    failures = 0
    for item in manifest["examples"]:
        body = json.loads((EXAMPLES / item["file"]).read_text(encoding="utf-8"))
        label = f"{item['method'].upper()} {item['path']} <= {item['file']}"
        try:
            validator_for(spec, item["schema"]).validate(body)
        except ValidationError as exc:
            failures += 1
            _print(f"FAIL  {label}: {exc.message}")
            continue
        _print(f"PASS  {label} ({item['schema']})")
    for item in manifest["rejects"]:
        label = item["name"]
        try:
            validator_for(spec, item["schema"]).validate(item["body"])
        except ValidationError:
            _print(f"PASS  rejected {label} ({item['schema']})")
            continue
        failures += 1
        _print(f"FAIL  {label} was accepted")
    return failures


def live_unauthenticated() -> int:
    failures = 0
    checks = (
        ("GET", "/", None, 200),
        ("GET", "/health", None, 200),
        ("GET", "/health/redis", None, 200),
        ("GET", "/openapi.json", None, 200),
    )
    for method, path, body, expect in checks:
        status, _headers, payload = _load(API + path, method)
        ok = status == expect and payload[:1] in (b"{", b"[")
        if path == "/" and ok:
            message = json.loads(payload).get("message", "")
            ok = "AnyMoment" in message
        if path == "/health" and ok:
            ok = json.loads(payload).get("status") == "healthy"
        _print(f"{'PASS' if ok else 'FAIL'}  live {method} {path} -> {status}")
        failures += 0 if ok else 1

    status, _headers, payload = _load(API + "/calendars")
    detail = json.loads(payload).get("detail")
    missing = (
        status == 422
        and isinstance(detail, list)
        and any(item.get("loc") == ["header", "x-auth-token"] for item in detail if isinstance(item, dict))
    )
    _print(f"{'PASS' if missing else 'FAIL'}  live GET /calendars without a credential -> {status}")
    failures += 0 if missing else 1

    status, _headers, payload = _load(
        API + "/calendars",
        headers={"Authorization": "Bearer am_live_00000000_notasecret"},
    )
    body = json.loads(payload)
    invalid = status == 401 and isinstance(body.get("detail"), dict) and body["detail"].get("code") == "invalid_api_key"
    _print(f"{'PASS' if invalid else 'FAIL'}  live GET /calendars with a bad Bearer key -> {status} invalid_api_key")
    failures += 0 if invalid else 1
    return failures


def main() -> int:
    spec = fetch_openapi()
    version = spec.get("info", {}).get("version")
    paths = spec.get("paths", {})
    _print(f"openapi {spec.get('openapi')} info.version {version} paths {len(paths)}")
    schema_failures = validate_examples(spec)
    live_failures = live_unauthenticated()
    _print("needs API key:")
    for item in KEY_CHECKS:
        _print(f"  - {item}")
    failures = schema_failures + live_failures
    _print(f"result: {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
