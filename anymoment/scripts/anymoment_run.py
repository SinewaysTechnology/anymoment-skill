"""Portable runner for AnyMoment CLI.

Usage:
  python skills/anymoment/scripts/anymoment_run.py -- <anymoment args...>

Behavior:
- Executes `anymoment` from PATH by default.
- Optional override: set `ANYMOMENT_BIN` to a full path to the `anymoment` executable.
- Forces UTF-8 IO env vars for predictable output.

Exit code matches underlying command.
"""

from __future__ import annotations

import os
import subprocess
import sys


def choose_anymoment_bin() -> str:
    return os.environ.get("ANYMOMENT_BIN") or "anymoment"


def main(argv: list[str]) -> int:
    if "--" in argv:
        idx = argv.index("--")
        args = argv[idx + 1 :]
    else:
        args = argv[1:]

    anymoment_bin = choose_anymoment_bin()
    cmd = [anymoment_bin, *args]

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    p = subprocess.run(cmd, env=env)
    return int(p.returncode)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
