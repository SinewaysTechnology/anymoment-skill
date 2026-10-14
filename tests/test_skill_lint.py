"""SKILL.md lint."""

from __future__ import annotations

import subprocess
import sys

import lint_skill
from conftest import ROOT

SKILL = ROOT / "SKILL.md"
FRONTMATTER = """---
name: anymoment
description: Read and write AnyMoment calendars. Use for agenda, create, and update.
---
"""


def _write_skill(directory, body: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(FRONTMATTER + "\n" + body + "\n", encoding="utf-8")


def test_current_skill_has_no_lint_errors():
    findings = lint_skill.lint_path(SKILL)
    errors = [item for item in findings if item.severity == "error"]
    assert errors == []


def test_current_skill_is_under_the_hard_budget():
    assert SKILL.stat().st_size <= lint_skill.HARD_BUDGET_BYTES
    findings = lint_skill.lint_path(SKILL)
    assert not any(item.code == "size" and item.severity == "error" for item in findings)


def test_repository_has_no_admin_endpoints():
    assert lint_skill.admin_hits(ROOT) == []


def test_lint_cli_exits_zero_and_reports_warnings():
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "lint_skill.py")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "skill lint: 0 errors," in completed.stdout
    assert "warning" in completed.stdout


def test_directory_mismatch_warns(tmp_path):
    skill_dir = tmp_path / "anymoment-skill"
    _write_skill(skill_dir, "Use `anymoment calendars list`.")
    findings = lint_skill.lint_path(skill_dir / "SKILL.md")
    assert any(item.code == "directory-name" and item.severity == "warning" for item in findings)


def test_directory_match_is_silent(tmp_path):
    skill_dir = tmp_path / "anymoment"
    _write_skill(skill_dir, "Use `anymoment calendars list`.")
    findings = lint_skill.lint_path(skill_dir / "SKILL.md")
    assert not any(item.code == "directory-name" for item in findings)


def test_invalid_frontmatter_is_an_error(tmp_path):
    skill_dir = tmp_path / "anymoment"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: Anymoment\ndescription: short\nextra: 1\n---\n",
        encoding="utf-8",
    )
    findings = lint_skill.lint_path(skill_dir / "SKILL.md")
    messages = [item.message for item in findings if item.code == "frontmatter"]
    assert any("lowercase" in message for message in messages)
    assert any("Unexpected fields" in message for message in messages)


def test_unbalanced_command_is_an_error(tmp_path):
    skill_dir = tmp_path / "anymoment"
    _write_skill(skill_dir, '`anymoment create "unterminated`')
    findings = lint_skill.lint_path(skill_dir / "SKILL.md")
    assert any(item.code == "command-parse" and item.severity == "error" for item in findings)


def test_unknown_subcommand_is_an_error(tmp_path):
    skill_dir = tmp_path / "anymoment"
    _write_skill(skill_dir, "`anymoment agenda explode --start PLACE`")
    findings = lint_skill.lint_path(skill_dir / "SKILL.md")
    assert any(item.code == "command-parse" for item in findings)


def test_pip_extra_brackets_parse(tmp_path):
    skill_dir = tmp_path / "anymoment"
    _write_skill(skill_dir, "`pip install anymoment[cli]`")
    findings = lint_skill.lint_path(skill_dir / "SKILL.md")
    assert not any(item.code == "command-parse" for item in findings)


def test_admin_endpoint_is_an_error(tmp_path):
    skill_dir = tmp_path / "anymoment"
    needle = "/auth/" + "admin/users"
    _write_skill(skill_dir, f"Never call {needle}.")
    findings = lint_skill.lint_path(skill_dir / "SKILL.md")
    assert any(item.code == "admin-endpoint" and item.severity == "error" for item in findings)


def test_over_hard_budget_is_an_error(tmp_path):
    skill_dir = tmp_path / "anymoment"
    _write_skill(skill_dir, "x" * (lint_skill.HARD_BUDGET_BYTES + 50))
    findings = lint_skill.lint_path(skill_dir / "SKILL.md")
    assert any(item.code == "size" and item.severity == "error" for item in findings)


def test_dated_example_is_detected(tmp_path):
    skill_dir = tmp_path / "anymoment"
    _write_skill(
        skill_dir,
        "`anymoment agenda list --start 2025-02-24T00:00:00 --end 2025-03-02T23:59:59`",
    )
    findings = lint_skill.lint_path(skill_dir / "SKILL.md")
    dated = [item for item in findings if item.code == "dated-example"]
    assert len(dated) == 2
    assert all(item.severity == "warning" for item in dated)


def test_skill_has_no_dated_examples():
    findings = lint_skill.lint_path(SKILL)
    dated = [item for item in findings if item.code == "dated-example"]
    assert dated == []


def test_skill_is_within_4kb_budget():
    findings = lint_skill.lint_path(SKILL)
    assert not any(item.code == "size" for item in findings)
    assert SKILL.stat().st_size <= lint_skill.SOFT_BUDGET_BYTES


def test_skill_warnings_are_only_the_directory_name():
    findings = lint_skill.lint_path(SKILL)
    assert [item.code for item in findings if item.severity == "warning"] == ["directory-name"]
    assert not any(item.severity == "error" for item in findings)


def test_cheat_sheet_stays_within_60_lines():
    assert len(SKILL.read_text(encoding="utf-8").splitlines()) <= 60


def test_documented_commands_parse():
    failures = []
    for relative in ("SKILL.md", "README.md", "references/cli.md", "CHANGELOG.md"):
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        for lineno, command in lint_skill.extract_commands(text):
            try:
                lint_skill.parse_command(command)
            except lint_skill.ParseError as exc:
                failures.append(f"{relative}:{lineno}: {command}: {exc}")
    assert failures == []


def test_api_key_and_subscription_commands_parse():
    commands = [
        "am auth status",
        "am auth status --json",
        'am calendars list --api-key "$ANYMOMENT_API_KEY"',
        "am events list --calendar CALENDAR --json",
        "am calendars subscriptions create CALENDAR --url URL --event-type event.updated",
        "am calendars subscriptions deliveries CALENDAR SUBSCRIPTION --limit 20",
        "am calendars subscriptions replay CALENDAR SUBSCRIPTION DELIVERY",
        "anymoment calendars subscriptions list CALENDAR",
        "anymoment calendars subscriptions get CALENDAR SUBSCRIPTION",
        "anymoment calendars subscriptions update CALENDAR SUBSCRIPTION --active",
        "anymoment calendars subscriptions delete CALENDAR SUBSCRIPTION --yes",
    ]
    for command in commands:
        lint_skill.parse_command(command)


def test_unknown_auth_subcommand_is_an_error(tmp_path):
    skill_dir = tmp_path / "anymoment"
    _write_skill(skill_dir, "`anymoment auth mint`")
    findings = lint_skill.lint_path(skill_dir / "SKILL.md")
    assert any(item.code == "command-parse" and item.severity == "error" for item in findings)


def test_skill_documents_api_key_setup():
    skill = SKILL.read_text(encoding="utf-8")
    reference = (ROOT / "references" / "cli.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for text in (skill, reference, readme):
        assert 'anymoment[cli]>=2.1.0' in text
        assert "ANYMOMENT_API_KEY" in text
        assert "--api-key" in text
        assert "am auth status" in text
    assert "never the secret" in skill
    assert "Do not print the key or write it to logs." in skill
    assert "Do not print or log the signing secret." in skill
    assert "verify_webhook" in skill
    assert "API keys" in skill
    assert "events:read" in skill
    assert "events:write" in skill
    assert "calendars:read" in skill
    assert "webhooks:manage" in skill
    assert "calendar-limited" in skill
    for code in (
        "invalid_api_key",
        "api_key_revoked",
        "api_key_expired",
        "api_key_not_permitted",
        "calendar_not_allowed",
        "retry_after",
    ):
        assert code in skill
        assert code in reference
    for phrase in (
        "Check the key in AnyMoment settings.",
        "This key was revoked.",
        "This key has expired.",
        "API keys cannot call sign-in, account, or key-management routes.",
        "Use `am auth login` for those.",
        "This key cannot access that calendar.",
        "GET /events",
        "am events list --calendar CALENDAR --json",
        "Wait `retry_after` seconds, then retry",
        "verify_webhook",
        "X-AnyMoment-Signature",
        "X-AnyMoment-Timestamp",
        "X-AnyMoment-Delivery",
        "am calendars subscriptions create CALENDAR --url https://example.com/hooks/anymoment --event-type event.updated",
        "am calendars subscriptions deliveries CALENDAR SUBSCRIPTION --limit 20",
        "am calendars subscriptions replay CALENDAR SUBSCRIPTION DELIVERY",
        "Do not print the key, repeat it, or write it to logs.",
        "Do not print it again or write it to logs.",
    ):
        assert phrase in reference
    assert "## 2.1.0" in changelog
    assert "anymoment[cli]>=2.1.0" in changelog
    assert "invalid_api_key" in changelog
    assert "verify_webhook" in changelog
    assert ">=2.0.1" not in skill
    assert ">=2.0.1" not in readme
    assert ">=2.0.1" not in reference
