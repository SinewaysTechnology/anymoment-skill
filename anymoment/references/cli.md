# AnyMoment CLI reference (agent-facing)

Default: `anymoment` is installed and on PATH.

## Use-case first (primary commands)

### Create events (extract + create)

- `anymoment create "TEXT" [--calendar "name or ID"] [--context TEXT] [--timezone TZ] [--model high|low|mega] [--host URL] [--raw]`
- Uses **extract** endpoint: free-form text → one or more events created. `--calendar` optional; accepts calendar **name** or **ID**.
- Alias: `anymoment events create "TEXT" [same options]` (also uses extract).

### Update event

- `anymoment update <event-id> [--when "recurrence text"] [--title "name"] [--description "desc"] [--timezone TZ] [--model high|low|mega] [--host URL] [--raw]`
- At least one of `--when`, `--title`, `--description` required. `--when` updates schedule via natural language.
- Alias: `anymoment events update <event-id> [--when] [--title/--name] [--description] [same options]`.

### Agenda

- `anymoment agenda list [--start ISO] [--end ISO] [--calendar "name or ID(s), comma-separated"] [--no-cache] [--webhooks] [--raw] [--pipe]`
  - Events + instances in a time window. Omit `--calendar` for all calendars. `--calendar` accepts **name(s)** or **ID(s)**.
- `anymoment agenda search <query> [--start ISO] [--end ISO] [--calendar "name or ID(s)"] [--active|--inactive] [--limit N] [--offset N] [--no-instances] [--raw] [--pipe]`
  - Fuzzy search over events.

### List calendars

- `anymoment calendars list [--active/--inactive] [--limit N] [--offset N] [--raw] [--pipe]`
- Use names or IDs from here in `--calendar` elsewhere.

---

## Auth / identity

- `anymoment auth login [--host URL]` (interactive)
- `anymoment auth logout [--host URL]`
- `anymoment tokens list`
- `anymoment tokens clear`
- `anymoment users me [--raw]`

## Config

- `anymoment config set-url <url>`
- `anymoment config set-timezone <IANA_TZ>`
- `anymoment config set-calendar <calendar-id-or-name>`
- `anymoment config show`

Env overrides: `ANYMOMENT_BASE_URL`, `ANYMOMENT_DEFAULT_TIMEZONE`, `ANYMOMENT_DEFAULT_CALENDAR`.

## Calendars (other)

- `anymoment calendars create <name> [--description TEXT] [--timezone TZ] [--color COLOR] [--raw]`
- `anymoment calendars get <id> [--raw]`
- `anymoment calendars update <id> [--name NAME] [--description TEXT] [--timezone TZ] [--color COLOR] [--active/--inactive] [--raw]`
- `anymoment calendars delete <id>`
- `anymoment calendars share <id> <user-id> [--role ROLE] [--raw]`
- `anymoment calendars webhook-url <id> [--raw]`
- (add-event, remove-event, batch-add-events, batch-remove-events, update-share, unshare — see `anymoment calendars --help`)

## Events (other)

- `anymoment events list [--calendar "name or ID"] [--active/--inactive] [--limit N] [--offset N] [--minimal] [--raw] [--pipe]`
- `anymoment events get <event-id> [--raw]`
- `anymoment events delete <event-id>`
- `anymoment events toggle <event-id> [--raw]`
- `anymoment events instances <event-id> [--from DATE] [--to DATE] [--optimized] [--raw]`
- `anymoment events next <event-id> [--raw]`
- `anymoment events export <event-id> [--format ics|csv] [--from DATE] [--to DATE] [--out FILE]`

## Output modes

- **Default:** human-readable.
- **`--raw`:** full JSON.
- **`--pipe`:** IDs only (where supported; for piping).

Where `--calendar` is used, it accepts a calendar **name** or **ID** (and comma-separated names/IDs for agenda list/search).
