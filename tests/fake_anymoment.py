#!/usr/bin/env python3
"""Stand-in for the anymoment executable used by script tests.

Reads fixture paths and an exit code from the environment, records argv, and
prints the fixture bytes. It does not talk to the network.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    argv_out = os.environ.get("ANYMOMENT_ARGV_OUT")
    if argv_out:
        Path(argv_out).write_text(json.dumps(sys.argv[1:]), encoding="utf-8")

    env_out = os.environ.get("ANYMOMENT_ENV_OUT")
    if env_out:
        Path(env_out).write_text(
            json.dumps(
                {
                    "PYTHONUTF8": os.environ.get("PYTHONUTF8"),
                    "PYTHONIOENCODING": os.environ.get("PYTHONIOENCODING"),
                }
            ),
            encoding="utf-8",
        )

    stdout_file = os.environ.get("ANYMOMENT_STDOUT_FILE")
    if stdout_file:
        sys.stdout.write(Path(stdout_file).read_text(encoding="utf-8"))
    stderr_file = os.environ.get("ANYMOMENT_STDERR_FILE")
    if stderr_file:
        sys.stderr.write(Path(stderr_file).read_text(encoding="utf-8"))
    return int(os.environ.get("ANYMOMENT_EXIT", "0"))


if __name__ == "__main__":
    raise SystemExit(main())
