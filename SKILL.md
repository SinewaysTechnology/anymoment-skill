---
name: anymoment
description: Read and write AnyMoment calendars with the anymoment CLI 2.0. Use for today's agenda, free time, creating or updating events, and listing calendars.
---

# AnyMoment

Install once: `pip install "anymoment[cli]>=2.0.1"`. Export `ANYMOMENT_TOKEN` so auth stays non-interactive. On a TTY, `anymoment auth login` stores a token under `~/.anymoment/`.

Lead with today, and ask only for the keys you will relay:

`am today --json --fields events,failures`

## Always

- Prefer `am`. Add `--json` (or `--jsonl` for a list) and `--fields`. Skip `--raw`.
- Cheap flag list: `anymoment schema`.
- Windows are relative: today, tomorrow, this week, next week, next fri.
- Exit codes: 0 ok, 2 usage, 3 auth, 4 not found, 5 conflict, 6 rate limited, 7 remote or sync. Exit 0 can still include `failures` or `sync_warnings`. Read them.
- On a non-zero exit, stderr is `{"error": {"code", "status", "user_message", "next_step", "retry_after"}}`. Tell the user `user_message` and `next_step`. On exit 6, mention `retry_after`.

## Core

- Today, this week, next week: `am today --json --fields events,failures`, `am week --json --fields events,failures`, `am next --json --fields events,failures`
- Another window: `am agenda "tomorrow" --json --fields events,failures`
- Search: `am agenda search "standup" --json`
- Create: `am events create "Team sync Tuesdays at 2pm" --dry-run`, then the same command without `--dry-run`
- Update: `am update EVENT_ID --title "New name" --yes`
- Delete: `am rm EVENT_ID --yes`
- Calendars: `am ls --json --fields result`

## Relay

- Agenda JSON is `{events, failures}`. Name each failure (`event_name` and `message`) before suggesting a time.
- After a write, read `sync_warnings` and `google_export_warnings`. Say each `user_message` and `next_step`.
- `google_origin` or `external_origin.read_only` cannot be edited here. Say so, and do not retry the write.
- Confirm with the user before delete or update. Pass `--yes` only after that.

## More

Command map, batch input, and free-time steps: `references/cli.md`.
