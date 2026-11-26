# AnyMoment for n8n

Two integrations live here. Neither is published from this repository until someone runs the publish workflow on purpose.

- [templates/](templates/): core-node workflow "Run a workflow on the last business day of the month, skipping public holidays". AnyMoment calls a Webhook node. Setup and curl examples are in [templates/README.md](templates/README.md).
- [nodes/](nodes/): community package `n8n-nodes-anymoment`. The AnyMoment Trigger creates the rule and the webhook for you. The AnyMoment node lists, previews, and deletes rules and subscriptions.

Install and production checks: [TESTING.md](TESTING.md).
