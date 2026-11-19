# Last business day of the month

Workflow file: [last-business-day-of-month.json](last-business-day-of-month.json)

Title: **Run a workflow on the last business day of the month, skipping public holidays**

The template uses only core n8n nodes. AnyMoment calls the Webhook node when `occurrence.due` fires. A Code node checks the signature. The Month-end job node is a no-op you can replace with Slack, Sheets, or an HTTP Request.

Account: https://anymoment.sineways.tech/?ref=n8n-tpl-last-bizday

There is a free 30-day trial. Webhooks need Pro after the trial.

## Import

1. In n8n, open the workflow menu and choose Import from File.
2. Select `last-business-day-of-month.json`.
3. Open the Webhook node and copy the production URL. It looks like `https://<your-n8n>/webhook/last-business-day`.
4. Create a credential of type Crypto. Paste the subscription secret into HMAC Secret and select that credential on the HMAC node. The workflow file does not contain the secret.

The file contains no API key, no signing secret, and no calendar id.

## Create the rule and the webhook

API keys cannot create calendars (`POST /calendars` is not allowed for an API key). Create the calendar in AnyMoment, then copy its id.

Create an API key with `events:read`, `events:write`, and `webhooks:manage`.

```bash
API=https://api.anymoment.sineways.tech
KEY=am_live_your_key
CALENDAR_ID=your_calendar_id
WEBHOOK_URL=https://your-n8n.example/webhook/last-business-day
```

Create the monthly rule. `recurrence` `2` is monthly. `type` `last_business_day` is the last business day. `country` selects the public holiday set. Omit `business_calendar` only if you want Saturday and Sunday weekends and no holidays.

```bash
curl -sS -X POST "$API/events" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Month-end close",
    "roll": "none",
    "business_calendar": { "country": "US" },
    "components": [
      {
        "operator": "OR",
        "event_config": {
          "recurrence": 2,
          "start_time": "09:00",
          "timezone": "Europe/Madrid",
          "is_all_day": false,
          "config": { "interval": 1, "type": "last_business_day" }
        }
      }
    ]
  }'
```

Save the `id` from the response as `EVENT_ID`. Link the rule to the calendar. An empty body is valid.

```bash
curl -sS -X POST "$API/calendars/$CALENDAR_ID/events/$EVENT_ID" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Subscribe the calendar. `occurrence.due` is delivered only for events linked to that calendar, and only to subscriptions that list it.

```bash
curl -sS -X POST "$API/calendars/$CALENDAR_ID/subscriptions" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"$WEBHOOK_URL\",
    \"event_types\": [\"occurrence.due\"]
  }"
```

The create response includes `secret` once. Put it in the Crypto credential field HMAC Secret and select that credential on the HMAC node. Later list and get calls do not return the secret.

Preview the dates before you wait for the first call. The instances route needs a start and an end. It does not take a count.

```bash
curl -sS -G "$API/events/$EVENT_ID/instances" \
  -H "Authorization: Bearer $KEY" \
  --data-urlencode "start=2026-11-01T00:00:00Z" \
  --data-urlencode "end=2027-06-01T00:00:00Z" \
  --data-urlencode "optimized=true" \
  --data-urlencode "include_webhooks=false"
```

For the United States, the last weekday of May 2027 is Monday 31 May, which is Memorial Day, so the last business day is Friday 28 May. The last weekday of December 2027 is Friday 31 December, which is New Year's Day observed, so the last business day is Thursday 30 December.

## What the workflow checks

AnyMoment sends:

- `X-AnyMoment-Signature`: hex HMAC-SHA256
- `X-AnyMoment-Timestamp`: unix seconds
- `X-AnyMoment-Delivery`: delivery id

The signed message is `timestamp + "." + raw body`. The body is compact JSON with sorted keys. A Code node reads the raw bytes from the Webhook node (raw body is enabled) and builds that string. The Crypto node computes the HMAC with the credential secret. A second Code node compares the digests and allows a 300 second clock window. A mismatch answers 401. A match answers 200 and runs the Month-end job.

n8n 2 does not allow `require('crypto')` inside a Code node unless the instance turns that builtin on. This template uses the Crypto node so a default self-hosted n8n can verify the signature.

These headers and the `occurrence.due` payload are not listed in the OpenAPI document. The workflow follows the webhook contract the API sends. `event_types` in the spec is an open array of strings.

## Free fallback, and what it misses

You can fire on the last weekday with a Schedule Trigger plus a Code node that checks a Quartz `LW` expression (last weekday of the month). That does not know public holidays. It still runs on Memorial Day, Monday 31 May 2027, and on New Year's Day observed, Friday 31 December 2027. The AnyMoment rule skips both.

## Publish

1. Confirm the HMAC node uses the Crypto credential that holds the signing secret.
2. Publish the workflow.
3. Optional: replay a past delivery with `POST /calendars/{calendar_id}/subscriptions/{subscription_id}/deliveries/{delivery_id}/replay` to see an execution without waiting for month end.
