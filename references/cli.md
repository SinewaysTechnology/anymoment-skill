# AnyMoment CLI 2.2 (agent reference)

Requires `anymoment` / `am` from `pip install "anymoment[cli]>=2.2.0"`. AnyMoment 2.2 needs Python 3.10 or newer. Product home: https://anymoment.sineways.tech/?ref=clawhub-skill

Checked against `https://api.anymoment.sineways.tech/openapi.json` and `anymoment` 2.2.0 (`main` of anymoment-python).

## Auth

The user creates an API key in AnyMoment settings, in the API keys section. They choose access (`events:read`, `events:write`, `calendars:read`, `webhooks:manage`) and which calendars the key can use. The CLI does not create, rotate, or revoke keys.

Set `ANYMOMENT_API_KEY` for a job, or pass `--api-key` on one command. The client sends that value as `Authorization: Bearer <key>`. A session token is a different header, `x-auth-token`. Do not put the API key in `x-auth-token`. When a key is set, it is used instead of `ANYMOMENT_TOKEN` and instead of a saved login. Do not print the key, repeat it, or write it to logs.

Check with `am auth status`. It shows the method (`api_key`, `token`, `saved_login`, or `none`) and, for a key, the prefix (`am_live_` plus eight hex characters). It checks that credential with the server and reports `status`: `valid`, `expired`, `invalid`, or `unknown`. `unknown` means the server could not be reached. Retry `am auth status`. It never prints the secret. `am auth status --json` prints `method`, `key_prefix`, and `status`. If the prefix is unrecognized, the value is not a key of that shape. Do not print the value.

A session still works. Export `ANYMOMENT_TOKEN`, or on a TTY run `anymoment auth login` (stored under `~/.anymoment/`). Without a TTY, login needs `--email` and `--password`. `anymoment auth resend-verification` sends the verification email again. `anymoment auth logout` drops the saved token. A failed login does not write the token file.

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
| 7 | Remote or sync: HTTP 403, HTTP 402, HTTP 5xx, network, or a CalDAV failure. |

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

A call with no `Authorization` header and no `x-auth-token` is HTTP 422 (`Field required` on `x-auth-token`), exit 2. A bad Bearer key is HTTP 401 `invalid_api_key`, exit 3.

A calendar-limited key cannot call `GET /events`. Pass a calendar id: `am events list --calendar CALENDAR --json`. The client then calls `GET /calendars/{calendar_id}/events`. Each item is the event plus its link. Do not pass `--minimal` on that list. If the list is rejected and `next_step` says to pass a calendar id, run that command and do not retry without one.

On HTTP 429 the exit code is 6. Wait `retry_after` seconds, then retry the request. If `retry_after` is null, wait, then retry.

### 401, 402, and 403

- **401.** The credential is missing, unknown, revoked, or expired, or the email is not verified. Use the table above. Do not retry the same key.
- **402.** The published OpenAPI document does not declare HTTP 402 on any path. The CLI still maps an unexpected 402 to exit 7. If `status` is 402, tell the user the action needs Pro or an active trial. Do not mention a price. Do not send a pricing URL. Point them at https://anymoment.sineways.tech/?ref=clawhub-skill
- **403.** Permission. `api_key_not_permitted` and `calendar_not_allowed` are in the table. Outgoing webhooks also return 403 when the caller is not the calendar owner (`Only the calendar owner can manage outgoing webhooks`). A plan check on other paid routes returns 403 with a message that the subscription does not allow the action. Say that outgoing webhooks need Pro or an active trial. Same link as above. Do not quote a price from the response.

Creating a subscription can still return 201 when the plan does not cover webhooks. Read `paused_reason`. The value `subscription_required` means deliveries will not be sent. A paused delivery has `last_error` `subscription_required`. Tell the user the same plan fact. Do not treat 201 as proof that hooks will fire.

## Agenda

`am today`, `am week`, and `am next` are this day, this week, and next week. `am agenda "tomorrow"` and `am agenda "next fri"` take a relative window. The CLI resolves it in the config timezone.

`--json` agenda output:

```json
{"v":1,"events":[{"event":{},"instances":[{"start":"...","end":"...","is_all_day":false}]}],"failures":[],"summary":{"by_calendar":{},"by_month":{}},"window":"today"}
```

`summary.by_calendar` and `summary.by_month` are present on `am agenda list` and on a window such as `am agenda "tomorrow"`. Each failure has `event_id`, `event_name`, `message`, and may have `reason` and `is_google_synced`. Say the event name and the message before you suggest a meeting time.

Search: `am agenda search "standup" --json`.

ISO bounds, when a phrase is not enough: `anymoment agenda list --start START --end END --json --fields events,failures`. `scripts/date_ranges.py` still prints those bounds (`next-week`, or `--days-back` / `--days-forward`). Prefer a relative window when the CLI understands it.

## Writes

- Natural language: `am events create "Team sync Tuesdays at 2pm" --calendar Work --dry-run`, then drop `--dry-run`. This calls the text parser. It is the wrong tool for a business-day rule.
- Exact fields, no business-day rule: `am events add --title "Dentist" --start START --end END --timezone Europe/Madrid --dry-run`, then drop `--dry-run`. `--rrule` accepts `FREQ=DAILY`, `WEEKLY`, `MONTHLY`, or `YEARLY` only. It cannot express a business day, a holiday calendar, or `roll`. `--location` is stored as a `Location:` line in the description. `POST /events` has no location field.
- Import an iCalendar file: `am events import FILE.ics --calendar CALENDAR --json`.
- Update: `am update EVENT_ID --when "every Tuesday at 11am" --title "New name" --yes`.
- Delete: `am rm EVENT_ID --yes`.
- Toggle: `anymoment events toggle EVENT_ID --json`.
- Link: `anymoment calendars add-event CALENDAR EVENT_ID --json`.
- Unlink: `anymoment calendars remove-event CALENDAR EVENT_ID --json`.

A successful write can include `sync_warnings` or `google_export_warnings`. Relay each `user_message` and any `next_step`.

`google_origin: true`, or `external_origin.read_only: true`, means the event is a mirror. Do not update or delete it. Tell the user to edit the source calendar.

Recurrence in natural language belongs in the create or `--when` text: "every Monday", "weekdays at 9am", "on the 1st of every month". A single day without "every" is one event: "dentist next Friday at 10am". No clock time means all day.

`POST /events/from-recurrence-text` accepts `model` `high`, `low`, or `mega`. The preview route accepts only `high` or `low`. Do not send `mega` to the preview.

## Business days

Say these with `POST /events` (`AdvancedRecurrentEventCreate`). Do not send a flat recurrence object. The body is `name`, `components`, and optional `roll` and `business_calendar`. The first component uses operator `OR`.

`am events add` and `Client.create_event` / `Client.create_scheduled_event` in anymoment 2.2.0 do not send `roll` or `business_calendar`. An RRULE cannot say "last business day". Post the JSON yourself with `Authorization: Bearer`. Then link it: `am calendars add-event CALENDAR EVENT_ID --json`. The link body may be `{}`.

Recurrence integers on `event_config.recurrence`:

| Value | Meaning | Config |
|------|---------|--------|
| 0 | Every N days | `interval` |
| 1 | Every N weeks | `interval`, `days_of_week` (0 Monday through 6 Sunday) |
| 2 | Every N months | `interval`, `type`, plus the fields below |
| 3 | Every N years | `interval`, `month`, `day` |
| 4 | Once | `scheduled_datetime` |
| 5 | Every day in ISO weeks | `interval`, `weeks_of_year` |
| 6 | Every day in months | `interval`, `months` |

Monthly `type` is `day_of_month`, `day_of_week`, `nth_business_day`, or `last_business_day`.

- Last business day: `"type": "last_business_day"`.
- First business day: `"type": "nth_business_day", "n": 1`.
- Nth business day: `"type": "nth_business_day", "n": 3` counts from the start of the month. `"from_end": true` counts from the end. `n` is required for `nth_business_day`. `week_of_month` 5 means last weekday of that weekday, which is not a business-day rule.
- Clock time is `start_time` / `end_time` as `HH:MM` in `event_config.timezone` (IANA, default UTC). All-day events set `is_all_day` true and omit both times.

`roll` runs after the dates are expanded, when a date is not a business day. Values: `none` (leave it), `forward`, `backward`, `nearest`, `skip` (drop it). Default is `none`. Put `roll` next to `components`, not inside `config`. Use it with `day_of_month` when the user wants "the 25th, or the previous business day".

`business_calendar` is the working calendar for business-day months and for `roll`. Omit it for Saturday and Sunday and no holidays.

- `country`: ISO 3166-1 alpha-2, such as `GB` or `US`.
- `subdiv`: holidays subdivision, such as `ENG` or `CA`.
- `weekend_days`: days off, 0 Monday through 6 Sunday. Default is Saturday and Sunday. Friday and Saturday is `[4, 5]`.
- `closures`: extra days off, `YYYY-MM-DD`.
- `extra_workdays`: working dates that override weekends, holidays, and closures.

Times on the wire for instances are requested with `start` and `end` (ISO datetimes). `GET /events/{event_id}/instances` requires both. `optimized=true` returns the id and the instances. `am events instances EVENT_ID --from FROM --to TO` sends query names `from` and `to`. Those names are not in the live spec. For a business-day check, call the API with `start` and `end` until the CLI is fixed.

Last business day, 09:00 Madrid, US holidays, default weekend:

```json
{
  "name": "Month-end close",
  "components": [
    {
      "operator": "OR",
      "event_config": {
        "recurrence": 2,
        "start_time": "09:00",
        "timezone": "Europe/Madrid",
        "config": {"interval": 1, "type": "last_business_day"}
      }
    }
  ],
  "business_calendar": {"country": "US"}
}
```

First business day, England holidays:

```json
{
  "name": "Month-open",
  "components": [
    {
      "operator": "OR",
      "event_config": {
        "recurrence": 2,
        "start_time": "09:00",
        "timezone": "Europe/London",
        "config": {"interval": 1, "type": "nth_business_day", "n": 1}
      }
    }
  ],
  "business_calendar": {"country": "GB", "subdiv": "ENG"}
}
```

Third business day from the end of the month:

```json
{
  "name": "Three days before month end",
  "components": [
    {
      "operator": "OR",
      "event_config": {
        "recurrence": 2,
        "start_time": "09:00",
        "timezone": "Europe/Madrid",
        "config": {"interval": 1, "type": "nth_business_day", "n": 3, "from_end": true}
      }
    }
  ]
}
```

The 25th, rolled backward onto a business day, Friday-Saturday weekend, one extra closure:

```json
{
  "name": "Pay day",
  "roll": "backward",
  "business_calendar": {
    "country": "IL",
    "weekend_days": [4, 5],
    "closures": ["2026-12-24"]
  },
  "components": [
    {
      "operator": "OR",
      "event_config": {
        "recurrence": 2,
        "start_time": "09:00",
        "timezone": "Asia/Jerusalem",
        "config": {"interval": 1, "type": "day_of_month", "day": 25}
      }
    }
  ]
}
```

The same JSON files live in `references/examples/` and are checked against the live OpenAPI schemas.

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

`am events add --file events.jsonl` is a different batch. Each object uses `title` (or `name`), `start`, `end`, `all_day`, `calendar`, `rrule`, `description`, `location`, and `timezone`. It still cannot set `roll` or `business_calendar`.

## Other commands

- Tokens: `anymoment tokens list`, `anymoment tokens clear`.
- Config: `anymoment config show`, `config set-url`, `config set-timezone`, `config set-calendar`.
- Calendars: `am ls`. Also `create`, `get`, `update`, `delete`, `share`, `update-share`, `unshare`, `webhook-url`, `subscriptions`, `batch-add-events`, `batch-remove-events`.
- Events: `list`, `get`, `instances`, `next`, `export`, `add`, `import`.
- Who am I: `anymoment users me --json`.
- Shell completion: `anymoment completion bash` (also `zsh` or `fish`).

Aliases: `am` is the binary, `a` is agenda, `ls` is calendars list, `rm` is events delete.

## Webhook subscriptions

Subscriptions belong to one calendar. Use a key whose access includes `webhooks:manage`, and a calendar that key allows. The caller must own the calendar. List and get do not include the signing secret.

Event types are `event.created`, `event.updated`, `event.deleted`, and `occurrence.due`. Repeat `--event-type` for more than one. An unknown type is rejected. `occurrence.due` is the delivery at an occurrence, not a CRUD notice.

```bash
am calendars subscriptions list CALENDAR
am calendars subscriptions create CALENDAR --url https://example.com/hooks/anymoment --event-type event.updated
am calendars subscriptions create CALENDAR --url https://example.com/hooks/anymoment --event-type occurrence.due --offset-seconds 0
am calendars subscriptions get CALENDAR SUBSCRIPTION
am calendars subscriptions update CALENDAR SUBSCRIPTION --url https://example.com/hooks/anymoment
am calendars subscriptions delete CALENDAR SUBSCRIPTION
am calendars subscriptions deliveries CALENDAR SUBSCRIPTION --limit 20
am calendars subscriptions replay CALENDAR SUBSCRIPTION DELIVERY
```

The create body is `url`, `event_types`, optional `secret`, and `occurrence_offset_seconds` (the CLI flag is `--offset-seconds`). The offset is seconds before (negative) or after the occurrence. It must sit inside 7 days, from -604800 to 604800. Default is 0.

The URL must be public HTTPS. Plain `http`, `localhost`, names ending in `.local`, and private IPs are rejected.

Omit `--secret` and AnyMoment generates a signing secret and returns it once, on create. Keep it for `verify_webhook`. Later responses do not include it. Do not print it again or write it to logs. If you pass `--secret`, it must be 16 to 256 characters, and you must not log the command. A caller-supplied secret is stored and not returned.

`occurrence.due` is queued for about the next 48 hours and sent at the occurrence start plus the offset. A monthly rule may show nothing until that window. Return any 2xx. A 4xx other than 408 or 429 is permanent. Other failures retry, up to 8 attempts.

Read `paused_reason` on the subscription. `subscription_required` means Pro or an active trial is missing, so deliveries pause. See the 401, 402, and 403 section. Do not mention a price.

### Payload

Version 1 fields, in the signed byte order (sorted keys, compact JSON, UTF-8): `calendar_id`, `change_type`, `event`, `event_id`, `occurrence_time`, `version`. `event` is `description`, `id`, `is_active`, `location`, `name`, `timezone`. `occurrence_time` is UTC for `occurrence.due` and null for the other types. `version` is 1.

```json
{"calendar_id":"...","change_type":"occurrence.due","event":{"description":null,"id":"...","is_active":true,"location":null,"name":"Month-end close","timezone":"Europe/Madrid"},"event_id":"...","occurrence_time":"2026-11-30T08:00:00+00:00","version":1}
```

Headers:

- `Content-Type: application/json`
- `User-Agent: AnyMoment-Webhooks/1`
- `X-AnyMoment-Signature`: hex HMAC-SHA256
- `X-AnyMoment-Timestamp`: unix seconds
- `X-AnyMoment-Delivery`: delivery id. It identifies the attempt and is not part of the signature.

`verify_webhook` from `anymoment` checks `X-AnyMoment-Signature`. The value is hex HMAC-SHA256 over `{timestamp}.{raw body}`. Pass the raw body bytes and the request headers (`X-AnyMoment-Signature`, `X-AnyMoment-Timestamp`, `X-AnyMoment-Delivery`). Re-encoding the JSON will not match. The helper also rejects a timestamp more than 300 seconds from now.

```python
from anymoment import verify_webhook

verify_webhook(raw_body, headers, secret)
```

The OpenAPI document describes subscription create and the delivery log. It does not list the event-type enum or the signed payload as its own schema. The payload above is the version 1 body the server signs. `DeliveryOut.payload` is an open object, so a delivery log row does not prove the signed field set.

## Scripts

- `python scripts/anymoment_run.py -- today --json --fields events,failures` runs the CLI with UTF-8 and `ANYMOMENT_BIN`.
- `scripts/anymoment_api.py` returns `.events`, `.failures`, `.sync_warnings`, `.user_message`, `.next_step`, and `.retry_after`.
- `python scripts/validate_examples.py` checks `references/examples/` against the live OpenAPI schemas and probes unauthenticated routes.
