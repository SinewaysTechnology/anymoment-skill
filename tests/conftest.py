"""Shared paths and a fake `anymoment` binary for script tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "http"
FAKE_ANYMOMENT = Path(__file__).resolve().parent / "fake_anymoment.py"

sys.path.insert(0, str(SCRIPTS))


class FakeCli:
    def __init__(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        self.monkeypatch = monkeypatch
        self.argv_path = tmp_path / "argv.json"
        self.env_path = tmp_path / "env.json"

    def install(
        self,
        *,
        stdout: Path | None = None,
        stderr: Path | None = None,
        code: int = 0,
    ) -> None:
        self.monkeypatch.setenv("ANYMOMENT_BIN", str(FAKE_ANYMOMENT))
        self.monkeypatch.setenv("ANYMOMENT_ARGV_OUT", str(self.argv_path))
        self.monkeypatch.setenv("ANYMOMENT_ENV_OUT", str(self.env_path))
        self.monkeypatch.setenv("ANYMOMENT_EXIT", str(code))
        if stdout is None:
            self.monkeypatch.delenv("ANYMOMENT_STDOUT_FILE", raising=False)
        else:
            self.monkeypatch.setenv("ANYMOMENT_STDOUT_FILE", str(stdout))
        if stderr is None:
            self.monkeypatch.delenv("ANYMOMENT_STDERR_FILE", raising=False)
        else:
            self.monkeypatch.setenv("ANYMOMENT_STDERR_FILE", str(stderr))

    def argv(self) -> list[str]:
        return json.loads(self.argv_path.read_text(encoding="utf-8"))

    def child_env(self) -> dict[str, str | None]:
        return json.loads(self.env_path.read_text(encoding="utf-8"))


@pytest.fixture
def cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeCli:
    return FakeCli(monkeypatch, tmp_path)
