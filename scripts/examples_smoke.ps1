# Smoke checks (manual). Set ANYMOMENT_API_KEY, or ANYMOMENT_TOKEN, or log in on a TTY first.
# am auth status shows the method and key prefix. Do not print the key.

anymoment schema
am auth status
am today --json --fields events,failures
am ls --json --fields result
# am events create "Standup every Monday at 9am" --dry-run
