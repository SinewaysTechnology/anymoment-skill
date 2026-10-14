# Changelog

## 2.1.0

Requires `anymoment[cli]>=2.1.0`.

- API keys are created in AnyMoment settings, in the API keys section. The user chooses access and calendars. Set `ANYMOMENT_API_KEY` or pass `--api-key`. `am auth status` shows the method and the key prefix, never the secret.
- Typed errors and next steps: `invalid_api_key`, `api_key_revoked`, `api_key_expired`, `api_key_not_permitted` (sign-in, account, and key-management routes), `calendar_not_allowed`, a calendar id on event listing for a calendar-limited key, and HTTP 429 `retry_after`.
- Calendar webhook subscriptions, and `verify_webhook` for the raw delivery body.

## 2.0.0

Requires `anymoment>=2.0.1`.

- Commands are JSON-first: prefer `am` with `--json` or `--jsonl` and `--fields`.
- Agenda commands return `{events, failures}`.
- Exit codes: 0 ok, 2 usage, 3 auth, 4 not found, 5 conflict, 6 rate limited, 7 remote or sync. Exit 0 can still include `failures` or `sync_warnings`.
