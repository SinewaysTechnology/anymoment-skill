# Smoke checks (manual). Set ANYMOMENT_TOKEN, or log in on a TTY first.

anymoment schema
am today --json --fields events,failures
am ls --json --fields result
# am events create "Standup every Monday at 9am" --dry-run
