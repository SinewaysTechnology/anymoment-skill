# AnyMoment skill

This folder is the **AnyMoment skill** for AI agents and humans: it teaches how to use the AnyMoment API via the `anymoment` CLI (create events from natural language, list agendas, find free time, manage calendars). The skill is AgentSkills-compatible (e.g. **OpenClaw**).

- Package: https://pypi.org/project/anymoment/
- SDK: https://github.com/SinewaysTechnology/anymoment-python
- Docs: https://anymoment.sineways.tech/anymoment-python/docs

## Install the CLI from PyPI

**Before using this skill**, install the AnyMoment CLI so the `anymoment` command is available:

```bash
pip install "anymoment[cli]>=2.1.0"
```

AnyMoment 2.1 requires Python 3.10 or newer.

- Use the same Python environment that your agent (e.g. OpenClaw) uses.
- **Verify:** run `anymoment --version`. If the command is not found, add the Python `Scripts` (Windows) or `bin` (Unix) directory to `PATH`, or set `ANYMOMENT_BIN` to the full path of the `anymoment` executable.
- **Then:** the user creates a key in AnyMoment settings, under API keys, and chooses access and calendars. Set `ANYMOMENT_API_KEY` (or pass `--api-key`). Check with `am auth status`. It shows the method and the key prefix, never the secret. Do not print the key or write it to logs. A session still works: export `ANYMOMENT_TOKEN`, or run `anymoment auth login` once on a TTY. Tokens are stored under `~/.anymoment/`. A key is used instead of a saved login or `ANYMOMENT_TOKEN`.

## What’s in this folder

| Path | Purpose |
|------|--------|
| **`SKILL.md`** | Short cheat sheet for agents. JSON-first, API keys, relative dates, exit codes, and what to tell the user. |
| **`references/cli.md`** | Command map, API key errors, webhook subscriptions, batch input, free-time steps, and write examples. |
| **`scripts/`** | Helpers: `anymoment_api.py` (JSON results with events, failures, and error fields), `anymoment_run.py` (UTF-8 + ANYMOMENT_BIN shim), `date_ranges.py` (ISO bounds when a phrase is not enough), `examples_smoke.ps1` (smoke commands). |

## Install and use with OpenClaw

1. **Clone the skill**

   ```bash
   git clone https://github.com/SinewaysTechnology/anymoment-skill
   ```

2. **Make the clone available to OpenClaw**  
   In `~/.openclaw/openclaw.json`, add the cloned folder (the one that contains `SKILL.md`) to `skills.load.extraDirs`. Use the absolute path of that clone:

   ```json
   {
     "skills": {
       "load": {
         "extraDirs": ["/path/to/anymoment-skill"]
       }
     }
   }
   ```

   Replace `/path/to/anymoment-skill` with the absolute path of the directory you cloned. OpenClaw discovers the skill from `SKILL.md` in that folder.

3. **Install the CLI from PyPI** (on the machine where OpenClaw runs):
   ```bash
   pip install "anymoment[cli]>=2.1.0"
   anymoment --version
   ```

4. **Authenticate** (same user/environment as OpenClaw). The user creates a key in AnyMoment settings, under API keys, and chooses access and calendars. Set `ANYMOMENT_API_KEY`, then:
   ```bash
   am auth status
   ```
   That shows the method and the key prefix. It does not print the secret. Do not print the key or write it to logs. `--api-key` sets the same credential for one command. A key is used instead of a saved login or `ANYMOMENT_TOKEN`. A session still works. Export `ANYMOMENT_TOKEN`, or on a TTY:
   ```bash
   anymoment auth login
   ```

5. **Use the skill in OpenClaw**  
   Ask the agent for calendar and scheduling tasks, e.g.:
   - *“What do I have this week?”*
   - *“Create a recurring standup every weekday at 9am.”*
   - *“When’s the best time to meet with John this week?”*

   The agent uses `SKILL.md` and `references/cli.md` in this folder to choose the right commands.

## Quick commands

| Goal | Command |
|------|--------|
| Which credential is in use? | `am auth status` |
| What’s on today? | `am today --json --fields events,failures` |
| What’s on this week? | `am week --json --fields events,failures` |
| Create events from text | `am events create "Your natural language here" --dry-run` |
| Update an event | `am update EVENT_ID --title "title" --yes` |
| Search events by name | `am agenda search "standup" --json` |
| List calendars | `am ls --json --fields result` |

The cheat sheet is **`SKILL.md`**. The command map and longer examples are in **`references/cli.md`**.
