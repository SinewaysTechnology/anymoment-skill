---
name: anymoment
description: Read and write AnyMoment calendars with the anymoment CLI 2.2. Use for today's agenda, free time, creating or updating events, business-day rules, occurrence.due webhooks, and listing calendars.
metadata:
  version: "2.2.0"
  homepage: "https://anymoment.sineways.tech/?ref=clawhub-skill"
---

# AnyMoment

Install once: `pip install "anymoment[cli]>=2.2.0"`.

The user creates a key in AnyMoment settings, under API keys, and chooses access (`events:read`, `events:write`, `calendars:read`, `webhooks:manage`) and calendars. The CLI does not create, rotate, or revoke keys. Set `ANYMOMENT_API_KEY`, or pass `--api-key` on one command. A key is sent as `Authorization: Bearer` and is used instead of `ANYMOMENT_TOKEN` or a saved login. Check with `am auth status`. It checks the credential with the server and reports `valid`, `expired`, `invalid`, or `unknown`. It shows the method and the key prefix, never the secret. Do not print the key or write it to logs. On a TTY, `anymoment auth login` still stores a session under `~/.anymoment/`.

Lead with today, and ask only for the fields you will relay:

`am today --json --fields events,failures`

## Always

- Prefer `am`. Add `--json` (or `--jsonl` for a list) and `--fields`. Skip `--raw`.
- Cheap flag list: `anymoment schema`.
- Windows are relative: today, tomorrow, this week, next week, next fri.
- Exit codes: 0 ok, 2 usage, 3 auth, 4 not found, 5 conflict, 6 rate limited, 7 remote or sync. Exit 0 can still include `failures` or `sync_warnings`. Read them.
- On a non-zero exit, stderr is `{"error": {"code", "status", "user_message", "next_step", "retry_after"}}`. Tell the user `user_message` and `next_step`. On exit 6, wait `retry_after` seconds, then retry.
- `invalid_api_key`: check the full key in settings, then set `ANYMOMENT_API_KEY` or `--api-key`. `api_key_revoked` or `api_key_expired`: create a new key in settings and replace `ANYMOMENT_API_KEY`. `api_key_not_permitted`: sign-in, account, and key-management routes need `am auth login`. `calendar_not_allowed`: choose a calendar this key allows. A calendar-limited key must pass a calendar id on `am events list --calendar CALENDAR --json`.
- HTTP 401 is a bad or missing credential (exit 3). HTTP 403 is permission (exit 7): the key, the calendar, or the plan. HTTP 402 is not in the published spec. If status is 402, or `paused_reason` is `subscription_required`, say outgoing webhooks need Pro or an active trial. Do not mention a price.

## Core

- Today, this week, next week: `am today --json --fields events,failures`, `am week --json --fields events,failures`, `am next --json --fields events,failures`
- Another window: `am agenda "tomorrow" --json --fields events,failures`
- Search: `am agenda search "standup" --json`
- Exact clock time, not a business-day rule: `am events add --title "Dentist" --start START --timezone Europe/Madrid --dry-run`, then drop `--dry-run`
- Natural language: `am events create "Team sync Tuesdays at 2pm" --dry-run`, then the same command without `--dry-run`
- Last, first, or nth business day, roll, a holiday calendar, or a custom weekend: do not use `--rrule`. Post the JSON in `references/cli.md`.
- Update: `am update EVENT_ID --title "New name" --yes`
- Delete: `am rm EVENT_ID --yes`
- Calendars: `am ls --json --fields result`
- Webhooks: `am calendars subscriptions create CALENDAR --url URL --event-type occurrence.due`. Check the raw body with `verify_webhook`. Do not print or log the signing secret.

## Relay

- Agenda JSON is `{events, failures}` and may include `summary`. Name each failure (`event_name` and `message`) before suggesting a time.
- After a write, read `sync_warnings` and `google_export_warnings`. Say each `user_message` and `next_step`.
- `google_origin` or `external_origin.read_only` cannot be edited here. Say so, and do not retry the write.
- Confirm with the user before delete or update. Pass `--yes` only after that.

## More

Business-day JSON, the `occurrence.due` payload, and API key errors: `references/cli.md`.
