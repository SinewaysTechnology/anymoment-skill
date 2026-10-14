"""Current behavior of scripts/anymoment_run.py."""

from __future__ import annotations

import anymoment_run
from conftest import FakeCli


def test_forwards_args_after_double_dash(cli: FakeCli):
    cli.install()
    code = anymoment_run.main(["anymoment_run.py", "--", "calendars", "list", "--raw"])
    assert code == 0
    assert cli.argv() == ["calendars", "list", "--raw"]


def test_forwards_args_without_double_dash(cli: FakeCli):
    cli.install()
    code = anymoment_run.main(["anymoment_run.py", "tokens", "list"])
    assert code == 0
    assert cli.argv() == ["tokens", "list"]


def test_exit_code_matches_the_cli(cli: FakeCli):
    cli.install(code=3)
    assert anymoment_run.main(["anymoment_run.py", "--", "auth", "login"]) == 3


def test_default_binary_name(monkeypatch):
    monkeypatch.delenv("ANYMOMENT_BIN", raising=False)
    assert anymoment_run.choose_anymoment_bin() == "anymoment"
