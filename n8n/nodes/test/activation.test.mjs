import assert from 'node:assert/strict';
import { test } from 'node:test';

import { anyMomentApiRequest } from '../dist/nodes/shared/api.js';
import { AnyMomentTrigger } from '../dist/nodes/AnyMomentTrigger/AnyMomentTrigger.node.js';

const BASE = 'https://api.example.test';

function node() {
	return {
		id: 'node-1',
		name: 'AnyMoment Trigger',
		type: 'n8n-nodes-anymoment.anyMomentTrigger',
		typeVersion: 1,
		position: [0, 0],
		parameters: {},
	};
}

function httpError(status, body, message) {
	return Object.assign(new Error(message ?? `Request failed with status code ${status}`), {
		statusCode: status,
		status,
		error: body,
		response: { status, statusText: String(status) },
	});
}

function hookContext(parameters, staticData, respond) {
	const calls = [];
	const context = {
		getNode: () => node(),
		getNodeParameter(name, fallback) {
			if (Object.prototype.hasOwnProperty.call(parameters, name)) return parameters[name];
			return fallback;
		},
		getWorkflowStaticData() {
			return staticData;
		},
		getNodeWebhookUrl() {
			return 'https://hooks.example.test/webhook/anymoment';
		},
		async getCredentials() {
			return { baseUrl: BASE, webhookSecret: '' };
		},
		helpers: {
			async httpRequestWithAuthentication(_credentialType, options) {
				const path = new URL(options.url).pathname;
				calls.push({ method: options.method, path });
				return respond({ method: options.method, path, calls });
			},
		},
	};
	return { context, calls };
}

function createParameters() {
	return {
		ruleMode: 'create',
		calendarId: 'cal-1',
		ruleName: 'Month end',
	};
}

function trigger() {
	return new AnyMomentTrigger();
}

test('anyMomentApiRequest puts the API error text on the thrown error', async () => {
	const { context } = hookContext({}, {}, () => {
		throw httpError(422, { error: 'https_required' });
	});
	await assert.rejects(
		() =>
			anyMomentApiRequest(context, 'POST', '/calendars/cal-1/subscriptions', { url: 'http://x' }),
		(error) => {
			assert.match(error.message, /https_required/);
			assert.equal(error.httpCode, '422');
			return true;
		},
	);
});

test('a deleted rule is recreated and a 409 link is success', async () => {
	const staticData = { createdEvent: true, eventId: 'evt-old' };
	const { context, calls } = hookContext(createParameters(), staticData, ({ method, path }) => {
		if (method === 'GET' && path === '/events/evt-old') {
			throw httpError(404, { error: 'gone' }, 'The resource you are requesting could not be found');
		}
		if (method === 'POST' && path === '/events') return { id: 'evt-new' };
		if (method === 'POST' && path === '/calendars/cal-1/events/evt-new') {
			throw httpError(
				409,
				{ error: 'event_on_calendar' },
				'Your request is invalid or could not be processed by the service',
			);
		}
		if (method === 'POST' && path === '/calendars/cal-1/subscriptions') {
			return { id: 'sub-1', secret: 'generated' };
		}
		throw new Error(`unexpected ${method} ${path}`);
	});

	const created = await trigger().webhookMethods.default.create.call(context);
	assert.equal(created, true);
	assert.deepEqual(
		calls.map((call) => `${call.method} ${call.path}`),
		[
			'GET /events/evt-old',
			'POST /events',
			'POST /calendars/cal-1/events/evt-new',
			'POST /calendars/cal-1/subscriptions',
		],
	);
	assert.equal(staticData.subscriptionId, 'sub-1');
	assert.equal(staticData.eventId, 'evt-new');
	assert.equal(staticData.createdEvent, true);
});

test('a 400 whose text says not found does not recreate the rule', async () => {
	const staticData = { createdEvent: true, eventId: 'evt-old' };
	const { context, calls } = hookContext(createParameters(), staticData, ({ method, path }) => {
		if (method === 'GET' && path === '/events/evt-old') {
			throw httpError(400, { detail: 'not found' });
		}
		throw new Error(`unexpected ${method} ${path}`);
	});

	await assert.rejects(
		() => trigger().webhookMethods.default.create.call(context),
		(error) => {
			assert.match(error.message, /not found/);
			assert.equal(error.httpCode, '400');
			return true;
		},
	);
	assert.deepEqual(
		calls.map((call) => call.method),
		['GET'],
	);
});

test('a new rule is deleted when the subscription cannot be created', async () => {
	const staticData = {};
	const { context, calls } = hookContext(createParameters(), staticData, ({ method, path }) => {
		if (method === 'POST' && path === '/events') return { id: 'evt-new' };
		if (method === 'POST' && path === '/calendars/cal-1/events/evt-new') return {};
		if (method === 'POST' && path === '/calendars/cal-1/subscriptions') {
			throw httpError(422, { error: 'https_required' });
		}
		if (method === 'DELETE' && path === '/events/evt-new') return { success: true };
		throw new Error(`unexpected ${method} ${path}`);
	});

	await assert.rejects(
		() => trigger().webhookMethods.default.create.call(context),
		(error) => {
			assert.match(error.message, /https_required/);
			assert.equal(error.httpCode, '422');
			return true;
		},
	);
	assert.deepEqual(
		calls.map((call) => `${call.method} ${call.path}`),
		[
			'POST /events',
			'POST /calendars/cal-1/events/evt-new',
			'POST /calendars/cal-1/subscriptions',
			'DELETE /events/evt-new',
		],
	);
	assert.equal(staticData.createdEvent, false);
	assert.equal(staticData.eventId, undefined);
});

test('an existing rule is kept when a later subscription create fails', async () => {
	const staticData = { createdEvent: true, eventId: 'evt-old' };
	const { context, calls } = hookContext(createParameters(), staticData, ({ method, path }) => {
		if (method === 'GET' && path === '/events/evt-old') return { id: 'evt-old' };
		if (method === 'PUT' && path === '/events/evt-old') return { id: 'evt-old' };
		if (method === 'POST' && path === '/calendars/cal-1/events/evt-old') return {};
		if (method === 'POST' && path === '/calendars/cal-1/subscriptions') {
			throw httpError(422, { error: 'https_required' });
		}
		throw new Error(`unexpected ${method} ${path}`);
	});

	await assert.rejects(
		() => trigger().webhookMethods.default.create.call(context),
		(error) => {
			assert.match(error.message, /https_required/);
			return true;
		},
	);
	assert.equal(
		calls.some((call) => call.method === 'DELETE'),
		false,
	);
	assert.equal(staticData.eventId, 'evt-old');
	assert.equal(staticData.createdEvent, true);
});

test('deactivating a subscription that is already gone succeeds', async () => {
	const staticData = { calendarId: 'cal-1', subscriptionId: 'sub-1' };
	const { context, calls } = hookContext(createParameters(), staticData, ({ method, path }) => {
		if (method === 'DELETE' && path === '/calendars/cal-1/subscriptions/sub-1') {
			throw httpError(404, { error: 'gone' }, 'The resource you are requesting could not be found');
		}
		throw new Error(`unexpected ${method} ${path}`);
	});

	const removed = await trigger().webhookMethods.default.delete.call(context);
	assert.equal(removed, true);
	assert.equal(staticData.subscriptionId, undefined);
	assert.equal(calls.length, 1);
});

test('deactivating still fails when the subscription delete is not a 404', async () => {
	const staticData = { calendarId: 'cal-1', subscriptionId: 'sub-1' };
	const { context } = hookContext(createParameters(), staticData, () => {
		throw httpError(500, { error: 'upstream_failed' });
	});

	await assert.rejects(
		() => trigger().webhookMethods.default.delete.call(context),
		(error) => {
			assert.match(error.message, /upstream_failed/);
			assert.equal(error.httpCode, '500');
			return true;
		},
	);
	assert.equal(staticData.subscriptionId, 'sub-1');
});
