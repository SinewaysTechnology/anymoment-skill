# AnyMoment skill

This folder is the **AnyMoment skill** for AI agents and humans: it teaches how to use the AnyMoment API via the `anymoment` CLI (create events from natural language, list agendas, find free time, manage calendars). The skill is AgentSkills-compatible (e.g. **OpenClaw**).

## Install the CLI from PyPI

**Before using this skill**, install the AnyMoment CLI so the `anymoment` command is available:

```bash
pip install "anymoment[cli]>=2.0.1"
```

- Use the same Python environment that your agent (e.g. OpenClaw) uses.
- **Verify:** run `anymoment --version`. If the command is not found, add the Python `Scripts` (Windows) or `bin` (Unix) directory to `PATH`, or set `ANYMOMENT_BIN` to the full path of the `anymoment` executable.
- **Then:** export `ANYMOMENT_TOKEN` for non-interactive use, or run `anymoment auth login` once on a TTY. Tokens are stored under `~/.anymoment/`.

## What’s in this folder

| Path | Purpose |
|------|--------|
| **`SKILL.md`** | Short cheat sheet for agents. JSON-first, relative dates, exit codes, and what to tell the user. |
| **`references/cli.md`** | Command map, batch input, free-time steps, and write examples. |
| **`scripts/`** | Helpers: `anymoment_api.py` (JSON results with events, failures, and error fields), `anymoment_run.py` (UTF-8 + ANYMOMENT_BIN shim), `date_ranges.py` (ISO bounds when a phrase is not enough), `examples_smoke.ps1` (smoke commands). |

## Install and use with OpenClaw

1. **Make the skill available to OpenClaw**  
   In `~/.openclaw/openclaw.json`, add this folder (the one that contains `SKILL.md`) to `skills.load.extraDirs`. Use the **absolute path to the `Skill` folder**:

   ```json
   {
     "skills": {
       "load": {
         "extraDirs": ["/path/to/AnyMoment/Skill"]
       }
     }
   }
   ```
   Replace `/path/to/AnyMoment/Skill` with your actual path to this `Skill` directory (e.g. `E:\work\Sineways\AnyMoment\Skill` on Windows). OpenClaw will discover the skill from the `SKILL.md` in this folder.

   **Or**, if the skill is published to ClawHub:
   ```bash
   clawhub install anymoment
   ```
   (Use the exact slug from ClawHub if different.)

2. **Install the CLI from PyPI** (on the machine where OpenClaw runs):
   ```bash
   pip install "anymoment[cli]>=2.0.1"
   anymoment --version
   ```

3. **Authenticate** (same user/environment as OpenClaw). Export `ANYMOMENT_TOKEN`, or on a TTY:
   ```bash
   anymoment auth login
   ```

4. **Use the skill in OpenClaw**  
   Ask the agent for calendar and scheduling tasks, e.g.:
   - *“What do I have this week?”*
   - *“Create a recurring standup every weekday at 9am.”*
   - *“When’s the best time to meet with John this week?”*

   The agent uses `SKILL.md` and `references/cli.md` in this folder to choose the right commands.

## Quick commands

| Goal | Command |
|------|--------|
| What’s on today? | `am today --json --fields events,failures` |
| What’s on this week? | `am week --json --fields events,failures` |
| Create events from text | `am events create "Your natural language here" --dry-run` |
| Update an event | `am update EVENT_ID --title "title" --yes` |
| Search events by name | `am agenda search "standup" --json` |
| List calendars | `am ls --json --fields result` |

The cheat sheet is **`SKILL.md`**. The command map and longer examples are in **`references/cli.md`**.
