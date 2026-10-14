# AnyMoment CLI 2.1 (agent reference)

Requires `anymoment` / `am` from `pip install "anymoment[cli]>=2.1.0"`. AnyMoment 2.1 needs Python 3.10 or newer.

## Auth

The user creates an API key in AnyMoment settings, in the API keys section. They choose access (`events:read`, `events:write`, `calendars:read`, `webhooks:manage`) and which calendars the key can use. The CLI does not create, rotate, or revoke keys.

Set `ANYMOMENT_API_KEY` for a job, or pass `--api-key` on one command. When either is set, it is used instead of `ANYMOMENT_TOKEN` and instead of a saved login. Do not print the key, repeat it, or write it to logs.

Check with `am auth status`. It shows the method (`api_key`, `token`, `saved_login`, or `none`) and, for a key, the prefix (`am_live_` plus eight hex characters). It never prints the secret, and it does not call the API. `am auth status --json` prints `method` and `key_prefix` only. If the prefix is unrecognized, the value is not a key of that shape. Do not print the value.

A session still works. Export `ANYMOMENT_TOKEN`, or on a TTY run `anymoment auth login` (stored under `~/.anymoment/`). Without a TTY, login needs `--email` and `--password`. `anymoment auth resend-verification` sends the verification email again. `anymoment auth logout` drops the saved token.

`--profile NAME` selects a config profile (`ANYMOMENT_PROFILE` does the same).

## Output

Put global flags after the subcommand.

- `--json` prints one compact object, wrapped as `{"v":1, ...}`.
- `--jsonl` prints one object per line when the payload is a list.
- `--fields events,failures` keeps `v` plus those top-level keys. It does not walk nested event fields.
- `--yes` skips the delete confirmation. Ask the user first, then pass it.
- `--dry-run` previews a write without sending it. Preview a create with `am events create ... --dry-run`.
- `--idempotency-key` remembers the first local result and replays it. The API does not take this key.
- `--api-key` sets the API key for this command. Same credential as `ANYMOMENT_API_KEY`. Do not log the value.
- `--raw` dumps the full document. Prefer `--json --fields`.

`anymoment schema` prints commands, aliases, flags, and exit codes. `anymoment help --json` prints that same document.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Ok. `failures` or `sync_warnings` may still be present. Read them. |
| 2 | Usage, HTTP 400, or HTTP 422. |
| 3 | Auth. Missing credential, HTTP 401, or an unverified email. |
| 4 | Not found. |
| 5 | Conflict. |
| 6 | Rate limited. Read `retry_after`. |
| 7 | Remote or sync: HTTP 403, HTTP 5xx, network, or a CalDAV failure. |

Stderr on a non-zero exit, when `--json` or `--jsonl` is set:

```json
{"error":{"code":null,"next_step":"...","retry_after":null,"status":429,"user_message":"..."}}
```

Tell the user `user_message` and `next_step`. Do not invent a next step when the field is null. These are the next steps for API key failures:

| Code | Status | Next step |
|------|--------|-----------|
| `invalid_api_key` | 401 | Check the key in AnyMoment settings. It starts with `am_live_`, then eight hex characters, an underscore, and the secret. Set `ANYMOMENT_API_KEY` or pass `--api-key`. Do not read the secret back. |
| `api_key_revoked` | 401 | This key was revoked. Create a new key in AnyMoment settings and replace `ANYMOMENT_API_KEY`. |
| `api_key_expired` | 401 | This key has expired. Create a new key in AnyMoment settings and replace `ANYMOMENT_API_KEY`. |
| `api_key_not_permitted` | 403 | API keys cannot call sign-in, account, or key-management routes. Use `am auth login` for those. Use the key for calendars, events, and webhook subscriptions. |
| `calendar_not_allowed` | 403 | This key cannot access that calendar. Choose a calendar the key allows. |

A calendar-limited key cannot call `GET /events`. Pass a calendar id: `am events list --calendar CALENDAR --json`. The client then calls `GET /calendars/{calendar_id}/events`. Each item is the event plus its link. Do not pass `--minimal` on that list. If the list is rejected and `next_step` says to pass a calendar id, run that command and do not retry without one.

On HTTP 429 the exit code is 6. Wait `retry_after` seconds, then retry the request. If `retry_after` is null, wait, then retry.

## Agenda

`am today`, `am week`, and `am next` are this day, this week, and next week. `am agenda "tomorrow"` and `am agenda "next fri"` take a relative window. The CLI resolves it in the config timezone.

`--json` agenda output:

```json
{"v":1,"events":[{"event":{},"instances":[{"start":"...","end":"...","is_all_day":false}]}],"failures":[],"window":"today"}
```

Each failure has `event_id`, `event_name`, `message`, and may have `reason` and `is_google_synced`. Say the event name and the message before you suggest a meeting time.

Search: `am agenda search "standup" --json`.

ISO bounds, when a phrase is not enough: `anymoment agenda list --start START --end END --json --fields events,failures`. `scripts/date_ranges.py` still prints those bounds (`next-week`, or `--days-back` / `--days-forward`). Prefer a relative window when the CLI understands it.

## Writes

- Create: `am events create "Team sync Tuesdays at 2pm" --calendar Work --dry-run`, then drop `--dry-run`.
- Update: `am update EVENT_ID --when "every Tuesday at 11am" --title "New name" --yes`.
- Delete: `am rm EVENT_ID --yes`.
- Toggle: `anymoment events toggle EVENT_ID --json`.
- Link: `anymoment calendars add-event CALENDAR EVENT_ID --json`.
- Unlink: `anymoment calendars remove-event CALENDAR EVENT_ID --json`.

A successful write can include `sync_warnings` or `google_export_warnings`. Relay each `user_message` and any `next_step`.

`google_origin: true`, or `external_origin.read_only: true`, means the event is a mirror. Do not update or delete it. Tell the user to edit the source calendar.

Recurrence belongs in the create or `--when` text: "every Monday", "weekdays at 9am", "on the 1st of every month". A single day without "every" is one event: "dentist next Friday at 10am". No clock time means all day.

## Free time

1. `am week --json --fields events,failures` (or `am agenda "tomorrow" --json --fields events,failures`). Omit `--calendar` so every calendar is included.
2. Relay every failure first.
3. Flatten `instances` to `[start, end]`, skip nothing that is busy, and sort by start.
4. Gaps inside the window that fit the meeting (30 or 60 minutes) are candidates. Prefer mid-morning through mid-afternoon unless the user asked for any time.
5. Offer one to three options in plain language, with the event names you used.

## Batch

`anymoment events batch --json` reads JSONL on stdin. Each line is one of:

```json
{"op":"create","text":"Standup every weekday at 9am"}
{"op":"update","id":"EVENT_ID","name":"New name"}
{"op":"delete","id":"EVENT_ID"}
{"op":"link","calendar_id":"CALENDAR","event_id":"EVENT_ID"}
```

## Other commands

- Tokens: `anymoment tokens list`, `anymoment tokens clear`.
- Config: `anymoment config show`, `config set-url`, `config set-timezone`, `config set-calendar`.
- Calendars: `am ls`. Also `create`, `get`, `update`, `delete`, `share`, `update-share`, `unshare`, `webhook-url`, `subscriptions`, `batch-add-events`, `batch-remove-events`.
- Events: `list`, `get`, `instances`, `next`, `export`.
- Who am I: `anymoment users me --json`.
- Shell completion: `anymoment completion bash` (also `zsh` or `fish`).

Aliases: `am` is the binary, `a` is agenda, `ls` is calendars list, `rm` is events delete.

## Webhook subscriptions

Subscriptions belong to one calendar. Use a key whose access includes `webhooks:manage`, and a calendar that key allows. List and get do not include the signing secret.

```bash
am calendars subscriptions list CALENDAR
am calendars subscriptions create CALENDAR --url https://example.com/hooks/anymoment --event-type event.updated
am calendars subscriptions get CALENDAR SUBSCRIPTION
am calendars subscriptions update CALENDAR SUBSCRIPTION --url https://example.com/hooks/anymoment
am calendars subscriptions delete CALENDAR SUBSCRIPTION
am calendars subscriptions deliveries CALENDAR SUBSCRIPTION --limit 20
am calendars subscriptions replay CALENDAR SUBSCRIPTION DELIVERY
```

Repeat `--event-type` for more than one type. `--offset-seconds` is optional. Delete asks on a terminal unless `--yes` is set. Confirm with the user first. Omit `--secret` and AnyMoment generates a signing secret and returns it once, on create. Keep it for `verify_webhook`. Later responses do not include it. Do not print it again or write it to logs. If you pass `--secret`, do not log the command.

`verify_webhook` from `anymoment` checks `X-AnyMoment-Signature`. The value is hex HMAC-SHA256 over `{timestamp}.{raw body}`. Pass the raw body bytes and the request headers (`X-AnyMoment-Signature`, `X-AnyMoment-Timestamp`, `X-AnyMoment-Delivery`). Re-encoding the JSON will not match. `X-AnyMoment-Delivery` identifies the attempt and is not part of the signature.

```python
from anymoment import verify_webhook

verify_webhook(raw_body, headers, secret)
```

## Scripts

- `python scripts/anymoment_run.py -- today --json --fields events,failures` runs the CLI with UTF-8 and `ANYMOMENT_BIN`.
- `scripts/anymoment_api.py` returns `.events`, `.failures`, `.sync_warnings`, `.user_message`, `.next_step`, and `.retry_after`.
