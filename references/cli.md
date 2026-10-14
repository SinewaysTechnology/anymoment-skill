# AnyMoment CLI 2.0 (agent reference)

Requires `anymoment` / `am` from `pip install "anymoment[cli]>=2.0.1"`.

Auth for a job: export `ANYMOMENT_TOKEN`. That skips the login prompt. On a TTY, `anymoment auth login` stores a token under `~/.anymoment/`. Without a TTY, login needs `--email` and `--password`. `anymoment auth resend-verification` sends the verification email again. `anymoment auth logout` drops the saved token.

`--profile NAME` selects a config profile (`ANYMOMENT_PROFILE` does the same).

## Output

Put global flags after the subcommand.

- `--json` prints one compact object, wrapped as `{"v":1, ...}`.
- `--jsonl` prints one object per line when the payload is a list.
- `--fields events,failures` keeps `v` plus those top-level keys. It does not walk nested event fields.
- `--yes` skips the delete confirmation. Ask the user first, then pass it.
- `--dry-run` previews a write without sending it. Preview a create with `am events create ... --dry-run`.
- `--idempotency-key` remembers the first local result and replays it. The API does not take this key.
- `--raw` dumps the full document. Prefer `--json --fields`.

`anymoment schema` prints commands, aliases, flags, and exit codes. `anymoment help --json` prints that same document.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Ok. `failures` or `sync_warnings` may still be present. Read them. |
| 2 | Usage, HTTP 400, or HTTP 422. |
| 3 | Auth. Missing token, HTTP 401, or an unverified email. |
| 4 | Not found. |
| 5 | Conflict. |
| 6 | Rate limited. Read `retry_after`. |
| 7 | Remote or sync: HTTP 403, HTTP 5xx, network, or a CalDAV failure. |

Stderr on a non-zero exit, when `--json` or `--jsonl` is set:

```json
{"error":{"code":null,"next_step":"...","retry_after":null,"status":429,"user_message":"..."}}
```

Tell the user `user_message` and `next_step`. Do not invent a next step when the field is null.

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
- Calendars: `am ls`. Also `create`, `get`, `update`, `delete`, `share`, `update-share`, `unshare`, `webhook-url`, `batch-add-events`, `batch-remove-events`.
- Events: `list`, `get`, `instances`, `next`, `export`.
- Who am I: `anymoment users me --json`.
- Shell completion: `anymoment completion bash` (also `zsh` or `fish`).

Aliases: `am` is the binary, `a` is agenda, `ls` is calendars list, `rm` is events delete.

## Scripts

- `python scripts/anymoment_run.py -- today --json --fields events,failures` runs the CLI with UTF-8 and `ANYMOMENT_BIN`.
- `scripts/anymoment_api.py` returns `.events`, `.failures`, `.sync_warnings`, `.user_message`, `.next_step`, and `.retry_after`.
