# Changelog

## 2.0.0

Requires `anymoment>=2.0.1`.

- Commands are JSON-first: prefer `am` with `--json` or `--jsonl` and `--fields`.
- Agenda commands return `{events, failures}`.
- Exit codes: 0 ok, 2 usage, 3 auth, 4 not found, 5 conflict, 6 rate limited, 7 remote or sync. Exit 0 can still include `failures` or `sync_warnings`.
