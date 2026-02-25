---
name: anymoment
description: Manage schedules, recurring events, and calendars via the AnyMoment CLI (`anymoment`). Use for listing calendars, creating/updating/deleting events, viewing agendas, expanding instances, exporting (ICS/CSV), and configuring defaults. Designed to be portable: assumes `anymoment` is installed and on PATH (or ANYMOMENT_BIN).
---

## Assumptions (portable)

- `anymoment` CLI is installed and available on `PATH`.
- Authentication is handled by the CLI (tokens/config under `~/.anymoment/`).
- Optional: set `ANYMOMENT_BIN` to a full path to the `anymoment` executable.

## Safety / operating rules

- Prefer **read-only** operations first (`calendars list`, `agenda list`, `events list`).
- Before destructive ops (`delete`, `toggle`, `update`), confirm the target ID; use `--raw` to preview when possible.
- For automation/parsing, use `--raw` (JSON) or `--pipe` (IDs only).

---

## Use cases (primary)

### 1. Create events from free-form text

Create one or more events by describing them in natural language. Uses the **extract** endpoint (extract + create in one step).

- **Command:** `anymoment create "Text describing events..." [--calendar "name or ID"]`
- Calendar is optional; if omitted, config default is used (or no calendar). `--calendar` accepts a calendar **name** or **ID**.
- Options: `--context`, `--timezone`, `--model high|low|mega`, `--host`, `--raw`.

Examples:

- `anymoment create "Standup every weekday at 9am and pay rent on the 1st of every month"`
- `anymoment create "Team sync Tuesdays 2pm" --calendar Work`
- `anymoment create "Dentist next Friday 10am" --timezone Europe/Madrid --raw`

Alias: `anymoment events create "..."` does the same (extract + create).

### 2. Edit an event

Update an event’s schedule (recurrence), title, and/or description. At least one of `--when`, `--title`, or `--description` is required.

- **Command:** `anymoment update <event_id> [--when "recurrence text"] [--title "new title"] [--description "new description"]`
- Options: `--timezone`, `--model`, `--host`, `--raw`.

Examples:

- `anymoment update abc-123 --title "New name"`
- `anymoment update abc-123 --when "Every Tuesday at 11am"`
- `anymoment update abc-123 --when "Weekdays 9-5" --title "Work hours"`

Alias: `anymoment events update <event_id> [--when] [--title/--name] [--description]` — same behavior.

### 3. Agenda (what’s coming up)

List events and instances in a time window, or search events by name.

- **List in window:**  
  `anymoment agenda list [--start <ISO>] [--end <ISO>] [--calendar "name or ID" (or comma-separated)] [--no-cache] [--webhooks] [--raw] [--pipe]`  
  Omit `--calendar` to use all calendars.

- **Search:**  
  `anymoment agenda search <query> [--start <ISO>] [--end <ISO>] [--calendar "name or ID(s)"] [--active|--inactive] [--limit N] [--raw] [--pipe]`

`--calendar` accepts calendar **name(s)** or **ID(s)** (comma-separated for multiple).

### 4. List calendars

Discover calendar names and IDs (use name or ID in `--calendar` elsewhere).

- **Command:** `anymoment calendars list`  
- Machine-friendly: `anymoment calendars list --raw` or `--pipe` (IDs only).

---

## Quick checks

- Who am I: `anymoment users me --raw`
- Tokens: `anymoment tokens list`
- Config: `anymoment config show`

## Defaults (recommended)

Set once so you can omit `--calendar` and `--timezone` in create/agenda:

- `anymoment config set-calendar <calendar-id-or-name>`
- `anymoment config set-timezone Europe/Madrid`

---

## Other commands

- **Auth:** `anymoment auth login [--host URL]`, `anymoment auth logout [--host]`
- **Config:** `anymoment config set-url <url>`, `anymoment config set-timezone <IANA>`, `anymoment config set-calendar <id>`, `anymoment config show`
- **Tokens:** `anymoment tokens list`, `anymoment tokens clear`
- **Events:** `anymoment events list [--calendar] [--raw] [--pipe]`, `anymoment events get <id> [--raw]`, `anymoment events delete <id>`, `anymoment events toggle <id> [--raw]`, `anymoment events instances <id> [--from DATE] [--to DATE] [--raw]`, `anymoment events next <id> [--raw]`, `anymoment events export <id> [--format ics|csv] [--from] [--to] [--out FILE]`
- **Calendars:** `anymoment calendars create <name> [--description] [--timezone] [--color]`, `anymoment calendars get <id>`, `anymoment calendars update/delete/share/...` (see `references/cli.md`)

Output modes: default (human-readable), `--raw` (JSON), `--pipe` (IDs only, where applicable).

## Scripts

- **date_ranges.py** — ISO start/end ranges:  
  `python scripts/date_ranges.py next-week --tz Europe/Madrid`  
  `python scripts/date_ranges.py --days-back 4 --days-forward 8 --tz Europe/Madrid`
- **anymoment_run.py** — UTF-8 + ANYMOMENT_BIN shim:  
  `python scripts/anymoment_run.py -- calendars list --raw`

## References

- `references/cli.md` — full command map and flags.
