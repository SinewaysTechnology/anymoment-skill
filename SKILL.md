---
name: anymoment
description: Manage schedules, recurring events, and calendars via the AnyMoment CLI (`anymoment`). Use for listing calendars, creating/updating/deleting events, viewing agendas, expanding instances, finding free time, and configuring defaults. Install the CLI from PyPI first; then use the skill.
---

## Install the CLI from PyPI

**Before using this skill**, install the AnyMoment CLI so the `anymoment` command is available. Prefer the official PyPI package:

```bash
pip install anymoment[cli]
```

- **With venv/conda:** Activate the environment first, then run the command above. The `anymoment` executable will be on `PATH` for that environment.
- **System-wide (Linux/macOS):** `pip install --user anymoment[cli]` or `sudo pip install anymoment[cli]` if you want it available for all users.
- **Windows:** `py -m pip install anymoment[cli]` or `pip install anymoment[cli]` from a terminal where Python is on PATH.

**Verify:** Run `anymoment --version`. If the command is not found, ensure the Python scripts directory (e.g. `Scripts` on Windows, `bin` on Unix) is on your `PATH`, or set `ANYMOMENT_BIN` to the full path of the `anymoment` executable.

**After install:** Run `anymoment auth login` once to authenticate; tokens are stored under `~/.anymoment/`. Then use the commands below.

## Assumptions (after install)

- `anymoment` CLI is installed (see above) and available on `PATH` (or `ANYMOMENT_BIN` points to it).
- Authentication is handled by the CLI (tokens/config under `~/.anymoment/`).
- Optional: set `ANYMOMENT_BIN` to a full path to the `anymoment` executable if it is not on `PATH`.

## Safety / operating rules

- Prefer **read-only** operations first (`calendars list`, `agenda list`, `events list`).
- Before destructive ops (`delete`, `toggle`, `update`), confirm the target ID; use `--raw` to preview when possible.
- For automation/parsing, use `--raw` (JSON) or `--pipe` (IDs only).

---

## Main use-case examples (questions → commands)

Map natural questions to CLI commands. Use the user's default timezone (from `anymoment config show`) for date ranges when not specified.

| User question | Approach | Example command(s) |
|---------------|----------|--------------------|
| **"What do I have this week?"** | Agenda for current week (Monday 00:00 – Sunday 23:59 in user TZ). Compute start/end as ISO, or use `date_ranges.py` if available. | `anymoment agenda list --start 2025-02-24T00:00:00 --end 2025-03-02T23:59:59` (adjust dates to current week; omit `--calendar` to include all calendars). |
| **"What happened on the 3rd of July?"** | Agenda for that **day** in the **past**. Assume current year if no year given. | `anymoment agenda list --start 2025-07-03T00:00:00 --end 2025-07-03T23:59:59` (use current year; for past years use the stated year). |
| **"What's on tomorrow?"** | Single day: tomorrow 00:00–23:59 in user TZ. | `anymoment agenda list --start <tomorrow 00:00 ISO> --end <tomorrow 23:59 ISO>`. |
| **"Do I have anything next Monday?"** | Single day: next Monday 00:00–23:59. | Same as above with that date. |
| **"When would be the best time to meet with John this week?"** | **Scheduling**: get agenda for the week across **all calendars** (omit `--calendar`), parse `--raw` JSON, identify free slots, then suggest 1–3 options with common sense (e.g. avoid first/last thing in the day if a "friendly" meeting, prefer 30–60 min gaps, consider work hours). See **Scheduling and finding free time** below. | `anymoment agenda list --start <week start ISO> --end <week end ISO> --raw` → parse instances, find gaps, suggest times. |
| **"Find a 30-minute slot for the team this week"** | Same as above: agenda list for the week, find a gap of ≥30 min, suggest it. | Same; filter gaps by duration. |
| **"What's on next week?"** | Next calendar week (Monday–Sunday). Use `date_ranges.py next-week --tz <TZ>` to get start/end ISO. | `anymoment agenda list --start <from script> --end <from script>` (omit `--calendar` for all). |
| **"What events do I have with 'standup' in the name?"** | Search by query; optionally narrow by time window. | `anymoment agenda search "standup" [--start ...] [--end ...]` (omit `--calendar` to search all calendars). |

**Date/time for queries:** If the user says "3rd of July" or "July 3" with no year, use **current year**. If they say "last Tuesday" or "next Friday", compute that date from today in the user's timezone. For "this week" use **Monday 00:00 to Sunday 23:59** in the user's default timezone (config or Europe/Madrid if unset). Use `scripts/date_ranges.py` when helpful: e.g. `next-week` for "next week", or `--days-back N --days-forward M --tz <TZ>` for custom ranges.

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

## Interpreting times, dates, and recurrence

When **answering questions** (agenda list/search), derive ISO start/end from the user's words:

- **No year** → use **current year** (e.g. "3rd of July" → July 3 of this year).
- **No month** → use **current month**; if that date has already passed (e.g. today is 28 Jan and they say "the 3rd"), use **next month** (3 Feb).
- **Relative days** → "tomorrow", "next Monday", "last Tuesday": compute from today in the user's default timezone.
- **Full day** vs **timed**: For **queries** you only pass a window (e.g. 00:00–23:59 for one day). The API returns both all-day and timed instances; you can show them as "all day" or "10:00 – 11:00" from the instance `start`/`end` and `is_all_day`.

When **creating or updating events** with `anymoment create` or `anymoment update --when`, the backend parses natural language into recurrence and times. Guide the user (or the agent) so that:

- **Recurrence** is used when the event **repeats**: e.g. "every Monday", "weekdays at 9am", "on the 1st of every month", "birthday on March 15th" (yearly). Use clear recurrence words: "every", "weekly", "monthly", "weekdays", "on Mondays".
- **One-off** events have **no** recurrence wording: e.g. "Meeting next Tuesday at 10am", "Dentist July 15 2025 at 2pm", "Conference from Monday 9am to Wednesday 5pm". A single weekday or single date without "every" is one-off.
- **Full-day** vs **timed**: If the user **does not mention a time**, the event is treated as all-day (e.g. "Team offsite every last Friday of the month"). If they **mention a time** (e.g. "at 9am", "from 9 to 5"), it is timed. Phrase create/update text accordingly.

(Internal parser rules: Monday=0 … Sunday=6; "weekdays" = Mon–Fri, "weekends" = Sat–Sun; time ranges as single "from X to Y"; bank holidays via special handling. You do not need to expose these; natural phrasing in create/update is enough.)

---

## Scheduling and finding free time

For questions like **"When would be the best time to meet with John this week?"** or **"Find a slot for a 1-hour call"**:

1. **Get all events in the window** from **all calendars** (omit `--calendar` so the agenda aggregates every calendar the user can access):
   - `anymoment agenda list --start <start ISO> --end <end ISO> --raw`
   - Use the window the user asked for ("this week", "next 5 days", etc.) in the user's default timezone.

2. **Parse the `--raw` JSON**: each item has `event` (name, id, …) and `instances` (array of `start`, `end`, `is_all_day`). Flatten all instances into a list of [start, end] (as datetime or comparable) and sort by start.

3. **Find free slots**: consider the window start and end; between consecutive instances (and before the first / after the last), any gap is a candidate. Filter to gaps that are at least as long as the requested meeting (e.g. 30 min or 1 hour).

4. **Suggest 1–3 options** using **common sense**:
   - Prefer slots that are not first thing in the morning or last thing in the evening unless the user prefers that.
   - Avoid back-to-back with very short gaps if the user might need buffer.
   - If the user said "meet with John", use the same data (all calendars may include shared or personal commitments); do not assume only one calendar matters.
   - If the user has a default working hours expectation (e.g. 9–17), you can restrict suggested slots to that range unless they asked for "any time".

5. **Reply in natural language**: e.g. "You’re free Tuesday 10:00–10:30, Wednesday 14:00–15:00, and Thursday 11:00–12:00. I’d suggest Wednesday 14:00 for a 1-hour call."

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
- Backend recurrence parser (for create/update semantics): in the AnyMoment API repo, `app/recurrence/parser/llm_documentation.md` — time handling, full-day vs timed, recurrence types, and when to use one-off vs recurring.
