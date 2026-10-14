"""SKILL.md lint. Target gaps that the current skill still has are xfail(strict=True)."""

from __future__ import annotations

import subprocess
import sys

import pytest

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


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="SKILL.md still contains hard-coded 2025 dates; the skill rewrite has not started",
)
def test_skill_has_no_dated_examples():
    findings = lint_skill.lint_path(SKILL)
    dated = [item for item in findings if item.code == "dated-example"]
    assert dated == []


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="SKILL.md is over the 4 KB budget; the cheat-sheet rewrite has not started",
)
def test_skill_is_within_4kb_budget():
    findings = lint_skill.lint_path(SKILL)
    assert not any(item.code == "size" for item in findings)
    assert SKILL.stat().st_size <= lint_skill.SOFT_BUDGET_BYTES
