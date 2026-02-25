# AnyMoment skill

This folder is the **AnyMoment skill** for AI agents and humans: it teaches how to use the AnyMoment API via the `anymoment` CLI (create events from natural language, list agendas, find free time, manage calendars). The skill is AgentSkills-compatible (e.g. **OpenClaw**).

## Install the CLI from PyPI

**Before using this skill**, install the AnyMoment CLI so the `anymoment` command is available:

```bash
pip install anymoment[cli]
```

- Use the same Python environment that your agent (e.g. OpenClaw) uses.
- **Verify:** run `anymoment --version`. If the command is not found, add the Python `Scripts` (Windows) or `bin` (Unix) directory to `PATH`, or set `ANYMOMENT_BIN` to the full path of the `anymoment` executable.
- **Then:** run `anymoment auth login` once. Tokens are stored under `~/.anymoment/`.

## What’s in this folder

| Path | Purpose |
|------|--------|
| **`SKILL.md`** | Main skill doc for agents: use cases, examples, scheduling, time/recurrence rules, install instructions. |
| **`references/cli.md`** | CLI command reference. |
| **`scripts/`** | Helpers: `date_ranges.py` (ISO date ranges), `anymoment_run.py` (UTF-8 + ANYMOMENT_BIN shim), `anymoment_api.py` (run helpers), `examples_smoke.ps1` (smoke commands). |

## Install and use with OpenClaw

1. **Make the skill available to OpenClaw**  
   In `~/.openclaw/openclaw.json`, add this folder (the one that contains `SKILL.md`) to `skills.load.extraDirs`. Use the **absolute path to the `Skill` folder**:

   ```json
   {
     "skills": {
       "load": {
         "extraDirs": ["/path/to/RepeatWiz/Skill"]
       }
     }
   }
   ```
   Replace `/path/to/RepeatWiz/Skill` with your actual path to this `Skill` directory (e.g. `E:\work\Sineways\RepeatWiz\Skill` on Windows). OpenClaw will discover the skill from the `SKILL.md` in this folder.

   **Or**, if the skill is published to ClawHub:
   ```bash
   clawhub install anymoment
   ```
   (Use the exact slug from ClawHub if different.)

2. **Install the CLI from PyPI** (on the machine where OpenClaw runs):
   ```bash
   pip install anymoment[cli]
   anymoment --version
   ```

3. **Log in once** (same user/environment as OpenClaw):
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
| Create events from text | `anymoment create "Your natural language here" [--calendar "name or ID"]` |
| Update an event | `anymoment update <event_id> [--when "recurrence"] [--title "title"] [--description "desc"]` |
| What’s on this week? | `anymoment agenda list --start <Mon 00:00 ISO> --end <Sun 23:59 ISO>` |
| Search events by name | `anymoment agenda search "standup"` |
| List calendars | `anymoment calendars list` |

Full use-case examples and the full command reference are in **`SKILL.md`** and **`references/cli.md`** in this folder.
