# Testing the n8n package

Nothing in this file publishes the package. Do not run the publish workflow and do not create a `n8n-nodes-anymoment-v*` tag unless you intend to publish.

## Install the tarball on self-hosted Docker n8n

Build the tarball on a machine that has this repo:

```bash
cd n8n/nodes
npm ci
npm run lint
npm run build
npm pack
```

`npm pack` writes `n8n-nodes-anymoment-0.1.0.tgz` in `n8n/nodes`. Copy that file into the n8n container and install it as the `node` user. The container name below is `n8n`. Change it if yours differs.

```bash
docker cp n8n-nodes-anymoment-0.1.0.tgz n8n:/tmp/n8n-nodes-anymoment-0.1.0.tgz
docker exec -u node n8n mkdir -p /home/node/.n8n/nodes
docker cp n8n-nodes-anymoment-0.1.0.tgz n8n:/home/node/.n8n/nodes/n8n-nodes-anymoment-0.1.0.tgz
docker exec -u node -w /home/node/.n8n/nodes n8n npm install ./n8n-nodes-anymoment-0.1.0.tgz
docker restart n8n
```

After the restart, search the node panel for **AnyMoment** and **AnyMoment Trigger**. Create a credential of type **AnyMoment API**.

A second option, useful when you are developing, is to point n8n at the built package instead of installing the tarball:

```bash
N8N_CUSTOM_EXTENSIONS=/absolute/path/to/n8n/nodes
```

The directory must contain `package.json` and a built `dist/` folder.

## Import the template

In the n8n editor: workflow menu, Import from File, `n8n/templates/last-business-day-of-month.json`.

Create a Crypto credential, put the subscription signing secret in HMAC Secret, and select it on the HMAC node before publishing. The workflow file does not contain the secret.

## Production end to end

You need an API key with `events:read`, `events:write`, `calendars:read`, and `webhooks:manage`. Create the calendar in the AnyMoment app first. API keys cannot call `POST /calendars`.

Account: https://anymoment.sineways.tech/?ref=n8n-node

```bash
API=https://api.anymoment.sineways.tech
KEY="$AM_API_KEY"
```

1. Credential test. In n8n, open the AnyMoment API credential and click the test button. It calls `GET /calendars?limit=1`. A 200 means the key is accepted. A 401 with `invalid_api_key` means the key was rejected. A 422 that asks for `x-auth-token` means the `Authorization` header was not sent as `Bearer am_live_...`.

2. Confirm the unauthenticated shapes (no key):

```bash
curl -sS "$API/"
curl -sS "$API/health"
curl -sS "$API/health/redis"
curl -sS -D - -o /dev/null "$API/calendars?limit=1"
```

The last call should be 422 with a missing `x-auth-token` header. Do not print the body of `/subscription/tiers` into tickets or docs. It includes prices.

3. Trigger. Create a workflow with **AnyMoment Trigger**, calendar selected, schedule **Last Business Day**, country `US`, time zone set. Activate it. Then:

```bash
curl -sS "$API/calendars/$CALENDAR_ID/subscriptions" -H "Authorization: Bearer $KEY"
```

You should see one subscription whose `url` is the n8n production webhook URL and whose `event_types` includes `occurrence.due`. Deactivate the workflow and list again. That subscription should be gone. The rule remains under `GET /events`.

4. Action node. On the same rule, run **Preview Next Dates** with count 6. Compare with:

```bash
curl -sS -G "$API/events/$EVENT_ID/instances" \
  -H "Authorization: Bearer $KEY" \
  --data-urlencode "start=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --data-urlencode "end=2028-01-01T00:00:00Z" \
  --data-urlencode "optimized=true" \
  --data-urlencode "include_webhooks=false"
```

5. Signed delivery. Replay a delivery, or wait for `occurrence.due`. The execution should contain `change_type` `occurrence.due` and `signatureValid` true. A body signed with the wrong secret should show an execution that stopped at 401 (the template) or no execution at all (the trigger node answers 401 before the workflow starts).

## Local mock used while developing

The package was exercised against a local mock that implements the same paths and the same signature bytes as the live API: create subscription on activate, signed `occurrence.due` POST, delete subscription on deactivate. Production was checked only on the unauthenticated routes above. A live key was not available in that environment.
