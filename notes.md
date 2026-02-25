# AnyMoment / RepeatWiz Skill - Implementation Notes

## Goal
Create a Clawdbot skill that allows the AI assistant to create, manage, and query calendar events on AnyMoment via a CLI tool.

---

## Implementation: Library-First Architecture with CLI

The project follows a **library-first** architecture where the core SDK is a Python library, and the CLI is a thin wrapper around it. This allows both programmatic and CLI usage.

**Benefits:**
- Token management handled by CLI/SDK (not in context)
- Skill stays tiny — just command examples
- CLI reusable outside Clawdbot (you/team can use it directly)
- Library can be used in Python scripts/automations
- Testable independently
- Same pattern as `gh` CLI / GitHub skill
- Ready for PyPI distribution

---

## Project Structure (Actual Implementation)

```
anymoment/
├── anymoment/
│   ├── __init__.py          # Package exports (Client, exceptions)
│   ├── client.py             # API wrapper (requests-based)
│   ├── config.py             # Configuration management
│   ├── exceptions.py         # Custom exception classes
│   ├── token_manager.py      # JWT caching with encryption
│   └── cli/
│       ├── __init__.py
│       └── commands.py       # Click commands (CLI entry point)
├── tests/
│   ├── conftest.py           # Pytest fixtures
│   ├── test_client.py
│   ├── test_cli.py
│   └── test_token_manager.py
├── pyproject.toml            # Package metadata & build config
├── requirements.txt          # Core dependencies
├── requirements-dev.txt      # Dev dependencies
├── README.md                 # Full documentation
└── LICENSE                   # MIT License
```

**Package Name:** `anymoment`  
**CLI Command:** `anymoment`  
**PyPI Ready:** Yes (configured in `pyproject.toml`)

### Token Management (Implemented)
- Store tokens in `~/.anymoment/tokens.json` (encrypted)
- Encrypt with Fernet (machine-derived key via PBKDF2HMAC)
- Support multiple hosts (dev, prod, etc.)
- Token expiry validation (checks JWT `exp` claim)
- Invalid tokens are automatically filtered out
- Clear with `anymoment tokens clear`

### Authentication Flow (Implemented)
1. First use: `anymoment auth login` → prompts for email/password → stores JWT
2. Subsequent uses: auto-uses cached token if valid
3. `--host` flag or `ANYMOMENT_BASE_URL` env var for different backends
4. Token expiry checked before each request
5. Graceful error messages when not authenticated

### Configuration Management (Implemented)
- Config stored in `~/.anymoment/config.json`
- Default API URL: `https://api.anymoment.sineways.tech`
- Default timezone: `UTC` (configurable)
- Default calendar ID: configurable
- Environment variable overrides: `ANYMOMENT_BASE_URL`, `ANYMOMENT_DEFAULT_TIMEZONE`, `ANYMOMENT_DEFAULT_CALENDAR`

---

## CLI Commands (Actual Implementation)

### Authentication
```bash
anymoment auth login [--host URL]          # Interactive login, cache token
anymoment auth logout [--host URL]          # Clear cached token for host
anymoment tokens list                       # Show cached tokens (host, expiry, status)
anymoment tokens clear                      # Clear all tokens
```

### Configuration
```bash
anymoment config set-url <url>              # Set default API URL
anymoment config set-timezone <tz>          # Set default timezone (IANA format)
anymoment config set-calendar <id>          # Set default calendar ID
anymoment config show                       # Show current config
```

### Calendars
```bash
anymoment calendars list [--active/--inactive] [--limit N] [--offset N] [--raw] [--pipe]
anymoment calendars create <name> [--description TEXT] [--timezone TZ] [--color COLOR] [--raw]
anymoment calendars get <id> [--raw]
anymoment calendars update <id> [--name NAME] [--description TEXT] [--timezone TZ] [--color COLOR] [--active/--inactive] [--raw]
anymoment calendars delete <id>
anymoment calendars share <id> <user-id> [--role ROLE] [--raw]
anymoment calendars webhook-url <id> [--raw]
```

### Events (Natural Language Creation)
```bash
anymoment events create "Meeting every Tuesday at 3pm" [--name NAME] [--description TEXT] [--timezone TZ] [--calendar ID] [--model high|low|mega] [--raw]
anymoment events create "Dentist appointment on Feb 15 at 10am" --calendar <id>
anymoment events create "Standup every weekday at 9am except holidays" --timezone "America/New_York"
```

### Events (CRUD Operations)
```bash
anymoment events list [--calendar ID] [--active/--inactive] [--limit N] [--offset N] [--minimal] [--raw] [--pipe]
# Note: For date filtering, use `events instances` instead

anymoment events get <event-id> [--raw]
anymoment events update <event-id> [--name NAME] [--description TEXT] [--raw]
anymoment events delete <event-id>
anymoment events toggle <event-id> [--raw]                    # Toggle active status
```

### Event Instances (Expanded Occurrences)
```bash
anymoment events instances <event-id> [--from DATE] [--to DATE] [--optimized] [--raw]
anymoment events next <event-id> [--raw]                      # Get next instance
anymoment events export <event-id> [--format ics|csv] [--from DATE] [--to DATE] [--out FILE]
```

### Calendar-Event Links
```bash
# Note: Link/unlink operations are available in the library API but not exposed as CLI commands yet
# Use the Python library for: link_event_to_calendar(), unlink_event_from_calendar()
```

### User Info
```bash
anymoment users me [--raw]                  # Show current user info
```

---

## Command Patterns (Actual Implementation)

### Common Options
- `--host, -h URL` — Override API host URL (env: `ANYMOMENT_BASE_URL`)
- `--raw` — Output full JSON response
- `--pipe` — Output only IDs (for piping/chaining commands)
- `--timezone, -z TZ` — Override timezone for this command (defaults to config)
- `--calendar, -c ID` — Specify calendar ID (defaults to config default)
- `--limit, -l N` — Limit number of results
- `--offset, -s N` — Skip N results (pagination)

### Output Formats (Implemented)
- **Default**: Human-readable format with status indicators ([OK]/[X]), counts, and formatted keys
- **`--raw`**: Full JSON response (for piping to `jq` or programmatic use)
- **`--pipe`**: Just IDs (for chaining commands: `anymoment calendars list --pipe | xargs -I {} anymoment calendars get {}`)

### Error Handling (Implemented)
- Custom exception hierarchy: `AnyMomentException` → `AuthenticationError`, `NotFoundError`, `ValidationError`, `ServerError`, `TokenError`, `ConfigError`
- Context-aware error messages with actionable guidance
- Proper exit codes (2 for auth errors, 1 for other errors)
- Graceful fallbacks and helpful prompts

### Sensible Defaults (Implemented)
- Timezone defaults to config value or UTC
- Calendar ID defaults to config value when available
- API URL defaults to config or `https://api.anymoment.sineways.tech`
- Clear messages when defaults are used

---

## Skill Structure (Ready for Implementation)

The CLI is fully implemented and ready. The skill should document the actual commands:

```
Skill/
├── SKILL.md              # Command examples and usage patterns
└── notes.md              # This file (implementation reference)
```

### SKILL.md Content (Recommended Structure)
```yaml
---
name: anymoment
description: Manage AnyMoment calendar events via CLI. Use for scheduling, reminders, recurring events, and calendar queries. Supports natural language event creation.
---

# AnyMoment CLI

Use the `anymoment` CLI to manage calendars and events. The CLI handles authentication, token management, and provides both human-readable and machine-readable output formats.

## Authentication

First-time setup:
```bash
anymoment auth login
```

## Create event (natural language)
```bash
anymoment events create "Meeting with John every Tuesday at 3pm" --calendar <calendar-id>
anymoment events create "Standup every weekday at 9am" --timezone "America/New_York"
```

## List events
```bash
anymoment events list --calendar <calendar-id>
anymoment events list --active  # Only active events
```

## Get event instances (for date filtering)
```bash
anymoment events instances <event-id> --from "2026-01-01" --to "2026-03-31"
anymoment events next <event-id>  # Get next occurrence
```

## Manage calendars
```bash
anymoment calendars list
anymoment calendars create "Work Calendar" --timezone "America/New_York"
anymoment calendars get <calendar-id>
```

## Configuration
```bash
anymoment config set-calendar <calendar-id>  # Set default calendar
anymoment config set-timezone "America/New_York"  # Set default timezone
anymoment config show  # View current config
```

## Output Formats
- Default: Human-readable with status indicators
- `--raw`: Full JSON for programmatic use
- `--pipe`: Just IDs for command chaining
```

---

## Implementation Status

### ✅ Phase 1: Core CLI (COMPLETED)
1. [x] Set up project structure (`pyproject.toml`, Click, library-first architecture)
2. [x] Implement `TokenManager` (encrypted storage with Fernet, PBKDF2HMAC key derivation)
3. [x] Implement `Client` class (API wrapper with requests, auto-retry on 401)
4. [x] `anymoment auth login` / `auth logout`
5. [x] `anymoment calendars list`
6. [x] `anymoment events create` (natural language)
7. [x] `anymoment events list`

### ✅ Phase 2: Full CRUD (COMPLETED)
8. [x] `anymoment events get/update/delete/toggle`
9. [x] `anymoment events instances` / `next`
10. [x] `anymoment events export` (ICS/CSV)
11. [x] `anymoment calendars create/update/delete/get/share/webhook-url`

### ✅ Phase 3: Configuration & User Info (COMPLETED)
12. [x] `anymoment config` commands (set-url, set-timezone, set-calendar, show)
13. [x] `anymoment users me`
14. [x] `anymoment tokens list` / `clear`

### ✅ Phase 4: Testing & Safety (COMPLETED)
15. [x] Comprehensive unit tests (37 tests, all passing)
16. [x] Test isolation (no real API calls, no real file I/O)
17. [x] Python 3.8+ compatibility
18. [x] Error handling and UX improvements
19. [x] Documentation (README.md)

### 📋 Phase 5: Skill Creation (READY)
20. [ ] Create `SKILL.md` with actual command examples
21. [ ] Test with Clawdbot/AI agent
22. [ ] Iterate based on real usage

### 🔮 Future Enhancements (Not Implemented)
- `anymoment advanced` commands (complex recurrence components)
- Calendar-event link/unlink CLI commands (available in library API)
- Interactive calendar selection prompts
- Local date parsing for simple cases

---

## Dependencies (Actual)

### Core Dependencies (Library)
```txt
requests>=2.28.0
pyjwt>=2.8.0
cryptography>=41.0.0
python-dateutil>=2.8.0
```

### CLI Dependencies (Optional)
```txt
click>=8.0.0  # Only needed if installing with [cli] extra
```

### Development Dependencies
```txt
pytest>=8.0.0
pytest-mock>=3.0.0
pytest-cov>=4.0.0
build>=1.0.0
twine>=4.0.0
```

### Installation
```bash
# Library only
pip install anymoment

# With CLI
pip install anymoment[cli]

# Development
pip install -e ".[cli]"
pip install pytest pytest-mock pytest-cov
```

---

## Design Decisions (Resolved)

1. **Calendar selection UX** ✅
   - Default calendar stored in config (`~/.anymoment/config.json`)
   - `--calendar` flag for explicit override
   - Defaults used automatically when not specified
   - Clear messages when defaults are applied

2. **Natural language date parsing** ✅
   - API's NL parser used for event creation (via `create_event_from_text`)
   - Date range parameters (`--from`, `--to`) accept ISO dates or natural language (handled by API)
   - `python-dateutil` included but primarily for local date handling if needed

3. **Webhook commands** ✅
   - Webhook generation included: `anymoment calendars webhook-url <id>`
   - Returns webhook URL for automation/integration use

4. **ICS export** ✅
   - Export command implemented: `anymoment events export <id> --format ics|csv`
   - Generates ICS/CSV files from event instances
   - Supports date range filtering

5. **Library-First Architecture** ✅
   - Core functionality in `Client` class (reusable)
   - CLI is thin wrapper around library
   - Both can be used independently
   - PyPI-ready for distribution

---

## Key Implementation Details

### Architecture
- **Library-First**: Core `Client` class provides all API functionality
- **CLI as Wrapper**: CLI commands call library methods
- **Modular Design**: Separate modules for client, config, token management, exceptions
- **Test Coverage**: 37 unit tests covering all major functionality

### Token Management
- Encrypted storage using Fernet (machine-specific key via PBKDF2HMAC)
- Multi-host support (dev, staging, prod)
- Automatic expiry validation
- Invalid tokens are filtered out with helpful error messages

### Error Handling
- Custom exception hierarchy for different error types
- Context-aware error messages
- Proper exit codes for scripting
- Graceful fallbacks and user guidance

### UX Features
- Sensible defaults (timezone, calendar ID from config)
- Status indicators ([OK]/[X]) for active/inactive items
- Multiple output formats (human-readable, JSON, IDs only)
- Helpful prompts and error messages
- Windows-compatible (ASCII-safe symbols)

### Testing Safety
- All tests use isolated temporary directories
- All API calls are mocked (no real HTTP requests)
- No real user data is modified during tests
- Automatic cleanup via pytest fixtures

### Python Compatibility
- Supports Python 3.8+ (uses `Optional` instead of `|` union syntax)
- Type hints compatible with older Python versions
- Uses `builtins.list`/`builtins.dict` to avoid shadowing issues

---

## Usage for AI Agents

When building a skill for an AI agent to use this CLI:

1. **Authentication**: Agent should run `anymoment auth login` first (or ensure token exists)
2. **Configuration**: Agent can set defaults with `anymoment config set-calendar` and `set-timezone`
3. **Event Creation**: Use natural language: `anymoment events create "TEXT"`
4. **Querying**: Use `anymoment events list` and `anymoment events instances` for date filtering
5. **Output Parsing**: Use `--raw` for JSON output or `--pipe` for IDs when chaining commands
6. **Error Handling**: Check exit codes (2 = auth error, 1 = other error)

### Example Agent Workflow
```bash
# 1. Check authentication
anymoment users me

# 2. List calendars to find one
anymoment calendars list --pipe  # Get IDs

# 3. Create event
anymoment events create "Team meeting every Monday at 10am" --calendar <id>

# 4. Get instances for next month
anymoment events instances <event-id> --from $(date +%Y-%m-%d) --to $(date -d "+1 month" +%Y-%m-%d) --raw
```

### Important Notes for Agents
- **Default Calendar**: Set with `anymoment config set-calendar <id>` to avoid specifying `--calendar` every time
- **Default Timezone**: Set with `anymoment config set-timezone <tz>` for consistent timezone handling
- **Token Management**: Tokens are automatically managed - no need to handle refresh manually
- **Error Recovery**: If auth fails, run `anymoment auth login` to re-authenticate
- **Output Formats**: Use `--raw` when parsing JSON, `--pipe` when chaining commands
- **Date Filtering**: Use `events instances` command with `--from` and `--to` for date ranges (not `events list`)
- **Command Structure**: Commands are grouped (e.g., `anymoment auth login`, not `anymoment login`)

---

*Created: 2026-01-28*  
*Updated: 2026-01-28*  
*Status: ✅ **IMPLEMENTED** — CLI fully functional, tested, and ready for skill creation*
