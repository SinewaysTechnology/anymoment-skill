---
name: anymoment
description: Read and write AnyMoment calendars with the anymoment CLI 2.1. Use for today's agenda, free time, creating or updating events, and listing calendars.
---

# AnyMoment

Install once: `pip install "anymoment[cli]>=2.1.0"`.

The user creates a key in AnyMoment settings, under API keys, and chooses access (`events:read`, `events:write`, `calendars:read`, `webhooks:manage`) and calendars. The CLI does not create, rotate, or revoke keys. Set `ANYMOMENT_API_KEY`, or pass `--api-key` on one command. A key is used instead of `ANYMOMENT_TOKEN` or a saved login. Check with `am auth status`. It shows the method and the key prefix, never the secret, and it does not call the API. Do not print the key or write it to logs. On a TTY, `anymoment auth login` still stores a session under `~/.anymoment/`.

Lead with today, and ask only for the fields you will relay:

`am today --json --fields events,failures`

## Always

- Prefer `am`. Add `--json` (or `--jsonl` for a list) and `--fields`. Skip `--raw`.
- Cheap flag list: `anymoment schema`.
- Windows are relative: today, tomorrow, this week, next week, next fri.
- Exit codes: 0 ok, 2 usage, 3 auth, 4 not found, 5 conflict, 6 rate limited, 7 remote or sync. Exit 0 can still include `failures` or `sync_warnings`. Read them.
- On a non-zero exit, stderr is `{"error": {"code", "status", "user_message", "next_step", "retry_after"}}`. Tell the user `user_message` and `next_step`. On exit 6, wait `retry_after` seconds, then retry.
- `invalid_api_key`: check the full key in settings, then set `ANYMOMENT_API_KEY` or `--api-key`. `api_key_revoked` or `api_key_expired`: create a new key in settings and replace `ANYMOMENT_API_KEY`. `api_key_not_permitted`: sign-in, account, and key-management routes need `am auth login`. `calendar_not_allowed`: choose a calendar this key allows. A calendar-limited key must pass a calendar id on `am events list --calendar CALENDAR --json`.

## Core

- Today, this week, next week: `am today --json --fields events,failures`, `am week --json --fields events,failures`, `am next --json --fields events,failures`
- Another window: `am agenda "tomorrow" --json --fields events,failures`
- Search: `am agenda search "standup" --json`
- Create: `am events create "Team sync Tuesdays at 2pm" --dry-run`, then the same command without `--dry-run`
- Update: `am update EVENT_ID --title "New name" --yes`
- Delete: `am rm EVENT_ID --yes`
- Calendars: `am ls --json --fields result`
- Webhooks: `am calendars subscriptions create CALENDAR --url URL --event-type event.updated`. Check the raw body with `verify_webhook`. Do not print or log the signing secret.

## Relay

- Agenda JSON is `{events, failures}`. Name each failure (`event_name` and `message`) before suggesting a time.
- After a write, read `sync_warnings` and `google_export_warnings`. Say each `user_message` and `next_step`.
- `google_origin` or `external_origin.read_only` cannot be edited here. Say so, and do not retry the write.
- Confirm with the user before delete or update. Pass `--yes` only after that.

## More

API key errors, subscriptions, batch input, and free-time steps: `references/cli.md`.
