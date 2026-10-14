#!/usr/bin/env python3
"""Check SKILL.md frontmatter, command syntax, size, and dated examples.

The soft size budget is 4 KB (warning). The hard size budget is 16 KB (error).
Hard-coded calendar dates and a skill-directory name mismatch are warnings.
"""

from __future__ import annotations

import os
import re
import shlex
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import yaml

SOFT_BUDGET_BYTES = 4 * 1024
HARD_BUDGET_BYTES = 16 * 1024

MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500
ALLOWED_FRONTMATTER_FIELDS = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}

# Built from parts so this file does not contain a contiguous admin path.
FORBIDDEN_ENDPOINTS = (
    "/auth/" + "admin",
    "/google/" + "admin",
    "/" + "admin/" + "logs",
)

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATED_EXAMPLE_PATTERNS = (
    re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}(?!\d)"),
    re.compile(
        rf"\b(?:{MONTHS})\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+(?:19|20)\d{{2}}\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{MONTHS})\s+(?:19|20)\d{{2}}\b",
        re.IGNORECASE,
    ),
)

INLINE_CODE = re.compile(r"`([^`\n]+)`")
COMMAND_START = re.compile(r"^(?:sudo\s+)?(?:anymoment|am|pip3?|python3?|py)(?:\s|$)")
BARE_TOOL = re.compile(r"^(?:sudo\s+)?(?:anymoment|am|pip3?|python3?|py)$")
GLOBAL_FLAGS = frozenset(
    {
        "--json",
        "--jsonl",
        "--fields",
        "--yes",
        "-y",
        "--dry-run",
        "--idempotency-key",
        "--profile",
        "--api-key",
    }
)
GLOBAL_VALUES = frozenset({"--fields", "--idempotency-key", "--profile", "--api-key"})
FENCE_LANGS = {"", "bash", "sh", "shell", "console"}

SCAN_SUFFIXES = {".md", ".py", ".yml", ".yaml", ".ps1", ".toml", ".txt", ".json"}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".venv", "venv"}


@dataclass(frozen=True)
class CommandSpec:
    flags: frozenset[str]
    positionals: int
    value_flags: frozenset[str]


def _leaf(flags: Iterable[str], positionals: int, value_flags: Iterable[str]) -> CommandSpec:
    return CommandSpec(frozenset(flags), positionals, frozenset(value_flags))


def _host_leaf(positionals: int = 0) -> CommandSpec:
    return _leaf(["--host", "-h"], positionals, ["--host", "-h"])


_CREATE_FLAGS = [
    "--calendar",
    "-c",
    "--context",
    "--timezone",
    "-z",
    "--model",
    "--host",
    "-h",
    "--raw",
    "--name",
    "--description",
]
_CREATE_VALUES = [
    "--calendar",
    "-c",
    "--context",
    "--timezone",
    "-z",
    "--model",
    "--host",
    "-h",
    "--name",
    "--description",
]
_UPDATE_FLAGS = [
    "--when",
    "--title",
    "--name",
    "--description",
    "--timezone",
    "-z",
    "--model",
    "--host",
    "-h",
    "--raw",
]
_UPDATE_VALUES = [
    "--when",
    "--title",
    "--name",
    "--description",
    "--timezone",
    "-z",
    "--model",
    "--host",
    "-h",
]
_AGENDA_FLAGS = [
    "--start",
    "-s",
    "--end",
    "-e",
    "--calendar",
    "-c",
    "--no-cache",
    "--webhooks",
    "--host",
    "-h",
    "--raw",
    "--pipe",
]
_AGENDA_VALUES = ["--start", "-s", "--end", "-e", "--calendar", "-c", "--host", "-h"]
_SEARCH_FLAGS = _AGENDA_FLAGS + [
    "--active",
    "--inactive",
    "--limit",
    "-l",
    "--offset",
    "--no-instances",
]
_SEARCH_VALUES = _AGENDA_VALUES + ["--limit", "-l", "--offset"]

# Subcommands of anymoment 2.1. Global agent flags are added in _check_args.
_WINDOW_FLAGS = ["--calendar", "-c", "--host", "-h", "--raw", "--pipe"]
_WINDOW_VALUES = ["--calendar", "-c", "--host", "-h"]
ANYMOMENT_COMMANDS: dict = {
    "--version": _leaf([], 0, []),
    "auth": {
        "login": _leaf(
            ["--host", "-h", "--email", "--password"],
            0,
            ["--host", "-h", "--email", "--password"],
        ),
        "resend-verification": _host_leaf(),
        "logout": _host_leaf(),
        "status": _host_leaf(),
    },
    "create": _leaf(_CREATE_FLAGS, 1, _CREATE_VALUES),
    "update": _leaf(_UPDATE_FLAGS, 1, _UPDATE_VALUES),
    "agenda": {
        "show": _leaf(_WINDOW_FLAGS, 1, _WINDOW_VALUES),
        "list": _leaf(_AGENDA_FLAGS, 0, _AGENDA_VALUES),
        "search": _leaf(_SEARCH_FLAGS, 1, _SEARCH_VALUES),
    },
    "today": _leaf(_WINDOW_FLAGS, 0, _WINDOW_VALUES),
    "week": _leaf(_WINDOW_FLAGS, 0, _WINDOW_VALUES),
    "next": _leaf(_WINDOW_FLAGS, 0, _WINDOW_VALUES),
    "schema": _leaf([], 0, []),
    "help": _leaf([], 1, []),
    "completion": _leaf([], 1, []),
    "calendars": {
        "list": _leaf(
            ["--active", "--inactive", "--limit", "-l", "--offset", "--raw", "--pipe"],
            0,
            ["--limit", "-l", "--offset"],
        ),
        "create": _leaf(
            ["--description", "--timezone", "-z", "--color", "--raw"],
            1,
            ["--description", "--timezone", "-z", "--color"],
        ),
        "get": _leaf(["--raw"], 1, []),
        "update": _leaf(
            [
                "--name",
                "--description",
                "--timezone",
                "-z",
                "--color",
                "--active",
                "--inactive",
                "--raw",
            ],
            1,
            ["--name", "--description", "--timezone", "-z", "--color"],
        ),
        "delete": _leaf([], 1, []),
        "share": _leaf(["--role", "--raw"], 2, ["--role"]),
        "webhook-url": _leaf(["--raw"], 1, []),
        "subscriptions": {
            "list": _leaf(["--host", "-h", "--raw"], 1, ["--host", "-h"]),
            "create": _leaf(
                [
                    "--url",
                    "--event-type",
                    "--secret",
                    "--offset-seconds",
                    "--host",
                    "-h",
                    "--raw",
                ],
                1,
                ["--url", "--event-type", "--secret", "--offset-seconds", "--host", "-h"],
            ),
            "get": _leaf(["--host", "-h", "--raw"], 2, ["--host", "-h"]),
            "update": _leaf(
                [
                    "--url",
                    "--event-type",
                    "--secret",
                    "--offset-seconds",
                    "--active",
                    "--inactive",
                    "--host",
                    "-h",
                    "--raw",
                ],
                2,
                ["--url", "--event-type", "--secret", "--offset-seconds", "--host", "-h"],
            ),
            "delete": _leaf(["--host", "-h"], 2, ["--host", "-h"]),
            "deliveries": _leaf(
                ["--limit", "-l", "--host", "-h", "--raw"],
                2,
                ["--limit", "-l", "--host", "-h"],
            ),
            "replay": _leaf(["--host", "-h", "--raw"], 3, ["--host", "-h"]),
        },
        "add-event": _leaf(
            ["--display-order", "--color", "--host", "-h", "--raw"],
            2,
            ["--display-order", "--color", "--host", "-h"],
        ),
        "remove-event": _leaf(["--host", "-h"], 2, ["--host", "-h"]),
        "batch-add-events": _leaf(
            ["--display-order", "--color", "--host", "-h", "--raw"],
            12,
            ["--display-order", "--color", "--host", "-h"],
        ),
        "batch-remove-events": _leaf(["--host", "-h"], 12, ["--host", "-h"]),
        "update-share": _leaf(["--role", "--host", "-h", "--raw"], 2, ["--role", "--host", "-h"]),
        "unshare": _leaf(["--host", "-h", "--raw"], 2, ["--host", "-h"]),
    },
    "users": {
        "me": _leaf(["--raw"], 0, []),
    },
    "tokens": {
        "list": _leaf([], 0, []),
        "clear": _leaf([], 0, []),
    },
    "config": {
        "set-url": _leaf([], 1, []),
        "set-timezone": _leaf([], 1, []),
        "set-calendar": _leaf([], 1, []),
        "show": _leaf([], 0, []),
    },
    "events": {
        "create": _leaf(_CREATE_FLAGS, 1, _CREATE_VALUES),
        "update": _leaf(_UPDATE_FLAGS, 1, _UPDATE_VALUES),
        "list": _leaf(
            [
                "--calendar",
                "-c",
                "--active",
                "--inactive",
                "--limit",
                "-l",
                "--offset",
                "--minimal",
                "--raw",
                "--pipe",
            ],
            0,
            ["--calendar", "-c", "--limit", "-l", "--offset"],
        ),
        "get": _leaf(["--raw"], 1, []),
        "delete": _leaf([], 1, []),
        "toggle": _leaf(["--raw"], 1, []),
        "instances": _leaf(["--from", "--to", "--optimized", "--raw"], 1, ["--from", "--to"]),
        "next": _leaf(["--raw"], 1, []),
        "export": _leaf(
            ["--format", "--from", "--to", "--out", "--raw"],
            1,
            ["--format", "--from", "--to", "--out"],
        ),
        "batch": _leaf(["--host", "-h"], 0, ["--host", "-h"]),
    },
}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    line: Optional[int] = None

    def format(self, path: str) -> str:
        loc = f"{path}:{self.line}" if self.line else path
        return f"{loc}: {self.severity}: {self.code}: {self.message}"


class ParseError(Exception):
    pass


def find_admin_endpoints(text: str) -> list[tuple[int, str]]:
    """Return (line, needle) for forbidden admin endpoint paths."""
    hits: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for needle in FORBIDDEN_ENDPOINTS:
            if needle in line:
                hits.append((lineno, needle))
    return hits


def admin_hits(root: Path) -> list[str]:
    """Scan the repo for admin endpoint paths. Empty means none were found."""
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        for filename in filenames:
            path = Path(dirpath) / filename
            if path.suffix.lower() not in SCAN_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for lineno, needle in find_admin_endpoints(text):
                rel = path.relative_to(root)
                found.append(f"{rel}:{lineno}: {needle}")
    return found


def _validate_name(name: object) -> list[str]:
    if not isinstance(name, str) or not name.strip():
        return ["Field 'name' must be a non-empty string"]
    normalized = unicodedata.normalize("NFKC", name.strip())
    errors: list[str] = []
    if len(normalized) > MAX_NAME_LENGTH:
        errors.append(
            f"Skill name '{normalized}' exceeds {MAX_NAME_LENGTH} characters ({len(normalized)})"
        )
    if normalized != normalized.lower():
        errors.append(f"Skill name '{normalized}' must be lowercase")
    if normalized.startswith("-") or normalized.endswith("-"):
        errors.append("Skill name cannot start or end with a hyphen")
    if "--" in normalized:
        errors.append("Skill name cannot contain consecutive hyphens")
    if not all(char.isalnum() or char == "-" for char in normalized):
        errors.append(
            f"Skill name '{normalized}' contains invalid characters. "
            "Only letters, digits, and hyphens are allowed."
        )
    return errors


def _validate_frontmatter(metadata: object) -> tuple[list[Finding], Optional[str]]:
    findings: list[Finding] = []
    if not isinstance(metadata, dict):
        findings.append(Finding("error", "frontmatter", "Frontmatter must be a YAML mapping"))
        return findings, None

    extra = sorted(set(metadata) - ALLOWED_FRONTMATTER_FIELDS)
    if extra:
        findings.append(
            Finding(
                "error",
                "frontmatter",
                "Unexpected fields in frontmatter: " + ", ".join(extra),
            )
        )

    name = metadata.get("name")
    if "name" not in metadata:
        findings.append(Finding("error", "frontmatter", "Missing required field: name"))
    else:
        for message in _validate_name(name):
            findings.append(Finding("error", "frontmatter", message))

    description = metadata.get("description")
    if "description" not in metadata:
        findings.append(Finding("error", "frontmatter", "Missing required field: description"))
    elif not isinstance(description, str) or not description.strip():
        findings.append(
            Finding("error", "frontmatter", "Field 'description' must be a non-empty string")
        )
    elif len(description) > MAX_DESCRIPTION_LENGTH:
        findings.append(
            Finding(
                "error",
                "frontmatter",
                f"Description exceeds {MAX_DESCRIPTION_LENGTH} characters ({len(description)})",
            )
        )

    compatibility = metadata.get("compatibility")
    if "compatibility" in metadata:
        if not isinstance(compatibility, str):
            findings.append(
                Finding("error", "frontmatter", "Field 'compatibility' must be a string")
            )
        elif len(compatibility) > MAX_COMPATIBILITY_LENGTH:
            findings.append(
                Finding(
                    "error",
                    "frontmatter",
                    f"Compatibility exceeds {MAX_COMPATIBILITY_LENGTH} characters ({len(compatibility)})",
                )
            )

    if "license" in metadata and not isinstance(metadata["license"], str):
        findings.append(Finding("error", "frontmatter", "Field 'license' must be a string"))
    if "allowed-tools" in metadata and not isinstance(metadata["allowed-tools"], str):
        findings.append(Finding("error", "frontmatter", "Field 'allowed-tools' must be a string"))

    meta = metadata.get("metadata")
    if "metadata" in metadata:
        if not isinstance(meta, dict):
            findings.append(Finding("error", "frontmatter", "Field 'metadata' must be a mapping"))
        else:
            for key, value in meta.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    findings.append(
                        Finding("error", "frontmatter", "Field 'metadata' values must be strings")
                    )
                    break

    clean_name = name.strip() if isinstance(name, str) else None
    return findings, clean_name


def parse_frontmatter(text: str) -> tuple[Optional[dict], Optional[str]]:
    """Return (metadata, error). metadata is None when the block cannot be parsed."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "SKILL.md must start with a YAML frontmatter block"
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        return None, "SKILL.md frontmatter is missing a closing ---"
    raw = "\n".join(lines[1:end])
    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return None, f"SKILL.md frontmatter is not valid YAML: {exc}"
    if loaded is None:
        return None, "SKILL.md frontmatter is empty"
    if not isinstance(loaded, dict):
        return None, "SKILL.md frontmatter must be a YAML mapping"
    return loaded, None


def _match_closer(text: str, start: int, open_char: str, close_char: str) -> int:
    depth = 0
    in_single = False
    in_double = False
    index = start
    while index < len(text):
        char = text[index]
        if in_single:
            if char == "'" and text[index - 1] != "\\":
                in_single = False
            index += 1
            continue
        if in_double:
            if char == "\\" and index + 1 < len(text):
                index += 2
                continue
            if char == '"':
                in_double = False
            index += 1
            continue
        if char == "'":
            in_single = True
        elif char == '"':
            in_double = True
        elif char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise ParseError(f"unbalanced {open_char}{close_char}")


def _substitute_placeholders(text: str) -> str:
    out: list[str] = []
    in_single = False
    in_double = False
    index = 0
    while index < len(text):
        char = text[index]
        if in_single:
            out.append(char)
            if char == "'" and text[index - 1] != "\\":
                in_single = False
            index += 1
            continue
        if in_double:
            out.append(char)
            if char == "\\" and index + 1 < len(text):
                out.append(text[index + 1])
                index += 2
                continue
            if char == '"':
                in_double = False
            index += 1
            continue
        if char == "'":
            in_single = True
            out.append(char)
            index += 1
            continue
        if char == '"':
            in_double = True
            out.append(char)
            index += 1
            continue
        if char == "<":
            close = text.find(">", index + 1)
            if close < 0:
                raise ParseError("unclosed '<' placeholder")
            out.append("PLACEHOLDER")
            index = close + 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _split_synopsis(text: str) -> tuple[str, list[str]]:
    """Split a synopsis into the base command and optional `[...]` groups.

    A `[` starts a group only when it is not attached to the previous word, so
    `anymoment[cli]` stays a single shell token.
    """
    base: list[str] = []
    groups: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == "[" and (index == 0 or text[index - 1].isspace()):
            close = _match_closer(text, index, "[", "]")
            groups.append(text[index + 1 : close])
            base.append(" ")
            index = close + 1
            continue
        if char == "]" and (index == 0 or text[index - 1].isspace()):
            raise ParseError("unbalanced []")
        base.append(char)
        index += 1
    return "".join(base), groups


def _strip_parentheticals(text: str) -> str:
    out: list[str] = []
    in_single = False
    in_double = False
    index = 0
    while index < len(text):
        char = text[index]
        if in_single:
            out.append(char)
            if char == "'" and text[index - 1] != "\\":
                in_single = False
            index += 1
            continue
        if in_double:
            out.append(char)
            if char == "\\" and index + 1 < len(text):
                out.append(text[index + 1])
                index += 2
                continue
            if char == '"':
                in_double = False
            index += 1
            continue
        if char == "'":
            in_single = True
            out.append(char)
        elif char == '"':
            in_double = True
            out.append(char)
        elif char == "(":
            close = _match_closer(text, index, "(", ")")
            index = close + 1
            continue
        else:
            out.append(char)
        index += 1
    return "".join(out)


def _split_pipes(text: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    in_single = False
    in_double = False
    for index, char in enumerate(text):
        if char == "'" and not in_double:
            in_single = not in_single
            buf.append(char)
            continue
        if char == '"' and not in_single and (index == 0 or text[index - 1] != "\\"):
            in_double = not in_double
            buf.append(char)
            continue
        if char == "|" and not in_single and not in_double:
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(char)
    parts.append("".join(buf))
    return parts


def _resolve_anymoment(argv: list[str]) -> CommandSpec:
    if not argv or argv[0] != "anymoment":
        raise ParseError("not an anymoment command")
    node: object = ANYMOMENT_COMMANDS
    rest = argv[1:]
    while rest and isinstance(node, dict):
        token = rest[0]
        if "/" in token and not token.startswith("-"):
            alternatives = [part for part in token.split("/") if part and part != "..."]
            if not alternatives:
                raise ParseError(f"unknown subcommand {token!r}")
            specs: list[CommandSpec] = []
            for alternative in alternatives:
                child = node.get(alternative)
                if isinstance(child, dict):
                    raise ParseError(f"incomplete subcommand {alternative!r}")
                if not isinstance(child, CommandSpec):
                    raise ParseError(f"unknown subcommand {alternative!r}")
                specs.append(child)
            flags: set[str] = set()
            value_flags: set[str] = set()
            for spec in specs:
                flags.update(spec.flags)
                value_flags.update(spec.value_flags)
            rest = rest[1:]
            return _check_args(
                CommandSpec(frozenset(flags), 0, frozenset(value_flags)),
                rest,
                allow_any_positionals=True,
            )
        if node is ANYMOMENT_COMMANDS and token == "ls":
            node = node["calendars"]["list"]
            rest = rest[1:]
            break
        if node is ANYMOMENT_COMMANDS and token == "rm":
            node = node["events"]["delete"]
            rest = rest[1:]
            break
        if node is ANYMOMENT_COMMANDS and token == "a":
            token = "agenda"
        child = node.get(token)
        if child is None and isinstance(node.get("show"), CommandSpec):
            node = node["show"]
            break
        if child is None:
            raise ParseError(f"unknown subcommand {token!r}")
        node = child
        rest = rest[1:]
        if isinstance(node, CommandSpec):
            break
    if isinstance(node, dict):
        raise ParseError("incomplete anymoment command")
    if not isinstance(node, CommandSpec):
        raise ParseError("unknown anymoment command")
    return _check_args(node, rest, allow_any_positionals=False)


def _with_globals(spec: CommandSpec) -> CommandSpec:
    return CommandSpec(
        spec.flags | GLOBAL_FLAGS,
        spec.positionals,
        spec.value_flags | GLOBAL_VALUES,
    )


def _check_args(spec: CommandSpec, rest: list[str], *, allow_any_positionals: bool) -> CommandSpec:
    spec = _with_globals(spec)
    positionals = 0
    index = 0
    while index < len(rest):
        token = rest[index]
        if token.startswith("-") and token != "-":
            if token not in spec.flags:
                raise ParseError(f"unknown flag {token}")
            index += 1
            if token in spec.value_flags and index < len(rest) and not rest[index].startswith("-"):
                index += 1
            continue
        positionals += 1
        index += 1
    # Synopses in the skill often name a command without every positional
    # (`anymoment create`, `anymoment update --when`). Extra words are still an error.
    if not allow_any_positionals and positionals > spec.positionals:
        raise ParseError(
            f"expected at most {spec.positionals} positional argument(s), found {positionals}"
        )
    return spec


def _validate_group(body: str, spec: CommandSpec) -> None:
    spec = _with_globals(spec)
    cleaned = _strip_parentheticals(body).strip()
    if not cleaned or cleaned == "...":
        return
    alias = re.fullmatch(r"(--[\w-]+)(?:/(--[\w-]+))+", cleaned)
    if alias:
        for flag in cleaned.split("/"):
            if flag not in spec.flags:
                raise ParseError(f"unknown flag {flag}")
        return
    for part in _split_pipes(cleaned):
        phrase = part.strip()
        if not phrase or phrase == "...":
            continue
        try:
            tokens = shlex.split(phrase)
        except ValueError as exc:
            raise ParseError(str(exc)) from exc
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if token == "..." or token == "PLACEHOLDER":
                index += 1
                continue
            if token.startswith("-"):
                if token not in spec.flags:
                    raise ParseError(f"unknown flag {token}")
                index += 1
                if index < len(tokens) and not tokens[index].startswith("-"):
                    index += 1
                continue
            index += 1


def parse_command(command: str) -> None:
    """Raise ParseError when a skill command cannot be parsed."""
    prepared = _substitute_placeholders(command.strip())
    base, groups = _split_synopsis(prepared)
    try:
        argv = shlex.split(base, posix=True)
    except ValueError as exc:
        raise ParseError(str(exc)) from exc
    if not argv:
        raise ParseError("empty command")
    for token in argv:
        for needle in FORBIDDEN_ENDPOINTS:
            if needle in token:
                raise ParseError(f"admin endpoint in command: {needle}")
    if argv[0] == "sudo":
        argv = argv[1:]
    if not argv:
        raise ParseError("empty command")
    if argv[0] == "am":
        argv[0] = "anymoment"
    if argv[0] != "anymoment":
        return
    spec = _resolve_anymoment(argv)
    for group in groups:
        _validate_group(group, spec)


def extract_commands(text: str) -> list[tuple[int, str]]:
    commands: list[tuple[int, str]] = []
    in_fence = False
    fence_lang = ""
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_fence:
                in_fence = True
                fence_lang = stripped[3:].strip().lower()
            else:
                in_fence = False
                fence_lang = ""
            continue
        if in_fence:
            if fence_lang in FENCE_LANGS and stripped and not stripped.startswith("#"):
                prompt = re.sub(r"^[$>]\s+", "", stripped)
                if COMMAND_START.match(prompt) and not BARE_TOOL.match(prompt):
                    commands.append((lineno, prompt))
            continue
        for match in INLINE_CODE.finditer(line):
            command = match.group(1).strip()
            if COMMAND_START.match(command) and not BARE_TOOL.match(command):
                commands.append((lineno, command))
    return commands


def _dated_examples(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        seen: set[str] = set()
        for pattern in DATED_EXAMPLE_PATTERNS:
            for match in pattern.finditer(line):
                value = match.group(0)
                if value in seen:
                    continue
                seen.add(value)
                findings.append(
                    Finding(
                        "warning",
                        "dated-example",
                        f"hard-coded date {value!r}",
                        lineno,
                    )
                )
    return findings


def _size_finding(size: int) -> Optional[Finding]:
    if size > HARD_BUDGET_BYTES:
        return Finding(
            "error",
            "size",
            f"SKILL.md is {size} bytes, above the hard budget of {HARD_BUDGET_BYTES} bytes",
        )
    if size > SOFT_BUDGET_BYTES:
        return Finding(
            "warning",
            "size",
            f"SKILL.md is {size} bytes, above the 4 KB budget ({SOFT_BUDGET_BYTES} bytes). "
            f"Hard limit is {HARD_BUDGET_BYTES} bytes.",
        )
    return None


def lint_text(
    text: str, *, skill_dir: Optional[Path] = None, size: Optional[int] = None
) -> list[Finding]:
    findings: list[Finding] = []
    metadata, error = parse_frontmatter(text)
    name: Optional[str] = None
    if error:
        findings.append(Finding("error", "frontmatter", error))
    else:
        field_findings, name = _validate_frontmatter(metadata)
        findings.extend(field_findings)

    if skill_dir is not None and name:
        dir_name = unicodedata.normalize("NFKC", skill_dir.name)
        skill_name = unicodedata.normalize("NFKC", name)
        if dir_name != skill_name:
            findings.append(
                Finding(
                    "warning",
                    "directory-name",
                    f"directory {dir_name!r} does not match frontmatter name {skill_name!r}",
                )
            )

    byte_size = size if size is not None else len(text.encode("utf-8"))
    size_finding = _size_finding(byte_size)
    if size_finding:
        findings.append(size_finding)

    findings.extend(_dated_examples(text))

    for lineno, needle in find_admin_endpoints(text):
        findings.append(
            Finding("error", "admin-endpoint", f"admin endpoint {needle!r} is not allowed", lineno)
        )

    for lineno, command in extract_commands(text):
        try:
            parse_command(command)
        except ParseError as exc:
            findings.append(Finding("error", "command-parse", f"{command}: {exc}", lineno))

    return findings


def lint_path(path: Path, skill_dir: Optional[Path] = None) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    directory = skill_dir if skill_dir is not None else path.parent
    return lint_text(text, skill_dir=directory, size=path.stat().st_size)


def _annotation(path: str, finding: Finding) -> str:
    kind = "warning" if finding.severity == "warning" else "error"
    line = f",line={finding.line}" if finding.line else ""
    return f"::{kind} file={path}{line}::{finding.code}: {finding.message}"


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[1]
    skill = Path(argv[1]) if len(argv) > 1 else root / "SKILL.md"
    if not skill.is_file():
        print(f"error: SKILL.md not found at {skill}", file=sys.stderr)
        return 1
    findings = lint_path(skill)
    rel = str(skill if not skill.is_absolute() else skill.name)
    errors = [item for item in findings if item.severity == "error"]
    warnings = [item for item in findings if item.severity == "warning"]
    for finding in findings:
        print(finding.format(rel))
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print(_annotation(rel, finding))
    print(f"skill lint: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
