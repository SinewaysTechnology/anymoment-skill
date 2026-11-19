# n8n-nodes-anymoment

n8n nodes for [AnyMoment](https://anymoment.sineways.tech/?ref=n8n-node). Create a monthly business-day rule, preview the dates it will fire, and receive `occurrence.due` when that moment arrives.

Get an API key: https://anymoment.sineways.tech/?ref=n8n-node

There is a free 30-day trial. Webhooks need Pro after the trial.

## Credentials

Create an **AnyMoment API** credential.

| Field | What to put |
| --- | --- |
| API Key | A key from the link above. Send it as `Authorization: Bearer`. The test request calls `GET /calendars?limit=1`, which needs `calendars:read`. |
| Webhook Signing Secret | Optional. If you set one, the trigger sends it when it creates the subscription and uses it to check `X-AnyMoment-Signature`. |
| Base URL | `https://api.anymoment.sineways.tech` unless you run your own API. |

A key limited to one calendar can list calendars and manage that calendar's subscriptions. It cannot call `GET /events`. On the Rule resource, use **By ID** for that kind of key.

API keys cannot create calendars. Create the calendar in AnyMoment first, then select it in the node.

## AnyMoment Trigger

Fires when AnyMoment delivers `occurrence.due`.

On activate, `webhookMethods` checks for an existing subscription on the same URL. If none exists it creates one. On deactivate it deletes that subscription. The rule itself stays, so the next activate updates it instead of leaving a duplicate.

**Create From Fields** posts a monthly rule:

- Schedule type: last business day, nth business day, day of month, or day of week.
- Interval, start time, time zone, all-day flag.
- Roll: none, forward, backward, nearest, or skip.
- Business calendar: country, subdivision, weekend days (Monday is 0), extra closure dates, extra workdays.

The trigger then links the rule to the calendar (`POST /calendars/{id}/events/{id}`) and subscribes that calendar to `occurrence.due`.

**Use an Existing Rule** only creates the subscription and the calendar link.

The node checks `X-AnyMoment-Signature` against the raw request body. A bad signature answers 401 and does not start the workflow. The default clock window is 300 seconds. Set it to 0 to check the signature and ignore the clock.

The one-time generated secret is stored in the workflow's static data, not in the workflow export.

## AnyMoment node

### Rule

| Operation | API |
| --- | --- |
| Preview Next Dates | `GET /events/{id}/instances` from now across the look-ahead window, then keeps the first N dates. There is no endpoint that previews a structured rule without saving it. |
| Create | `POST /events`, then an optional calendar link. |
| Get | `GET /events/{id}` |
| Get Many | `GET /events` |
| Get Next Instance | `GET /events/{id}/next-instance` |
| Delete | `DELETE /events/{id}` |

### Subscription

| Operation | API |
| --- | --- |
| Get Many | `GET /calendars/{id}/subscriptions` |
| Create | `POST /calendars/{id}/subscriptions` |
| Get | `GET /calendars/{id}/subscriptions/{id}` |
| Delete | `DELETE /calendars/{id}/subscriptions/{id}` |
| Get Many Deliveries | `GET .../deliveries` |
| Replay a Delivery | `POST .../deliveries/{id}/replay` |

## Example

1. Add **AnyMoment Trigger**.
2. Choose the calendar, leave the schedule on **Last Business Day**, and set the country (for example `US`).
3. Activate the workflow. AnyMoment creates the rule, links it, and subscribes this n8n URL.
4. Add an **AnyMoment** node on **Preview Next Dates**, point it at the same rule, and run it once to see the upcoming dates before the first delivery.

## What the OpenAPI spec does not describe

The live spec at `https://api.anymoment.sineways.tech/openapi.json` is the source for paths, bodies, and query parameters. A few things the nodes need are missing from that document. They follow the API source and the webhook notes in this repository, and they are called out here so they are not mistaken for spec fields.

- `occurrence.due` is not named. `event_types` is an open array of strings. The values the API actually sends are `event.created`, `event.updated`, `event.deleted`, and `occurrence.due`.
- The delivery body and the headers `X-AnyMoment-Signature`, `X-AnyMoment-Timestamp`, and `X-AnyMoment-Delivery` are not in the spec. The signature is hex HMAC-SHA256 over `timestamp + "." + raw body`, using the raw bytes (sorted compact JSON). Re-encoding the JSON will not match.
- `recurrence` is an integer enum `0` to `7` with no labels. Monthly rules in this node send `2`. The value `7` has no label in the spec or the recurrence guide.
- There is no preview endpoint for a structured rule. Preview Next Dates reads saved instances.
- `x-auth-token` and `authorization` are both marked optional. Production requires `x-auth-token` unless `Authorization: Bearer` carries an `am_live_` API key.
- A generated subscription secret is returned only by the create call. List and get omit it. A secret you supply is stored and not returned.
- The spec does not bound `occurrence_offset_seconds` or the secret length. The API source caps the offset at plus or minus 7 days and secrets at 16 to 256 characters. The node sends the values through and does not invent those limits as validation.
