# Smoke tests (manual)

anymoment --version
anymoment users me --raw
anymoment calendars list --raw
# Create (uses extract endpoint; requires default calendar or --calendar)
anymoment create "Standup every Monday at 9am" --raw
# Update (replace EVENT_ID with an event id from agenda list or events list)
# anymoment update EVENT_ID --title "New title" --raw
