import assert from 'node:assert/strict';
import { test } from 'node:test';

import { apiErrorText, httpStatus, isHttpStatus } from '../dist/nodes/shared/api.js';

test('httpStatus reads NodeApiError.httpCode when the message is generic', () => {
	const missing = {
		httpCode: '404',
		message: 'The resource you are requesting could not be found',
	};
	const conflict = {
		httpCode: '409',
		message: 'Your request is invalid or could not be processed by the service',
	};
	assert.equal(httpStatus(missing), 404);
	assert.equal(isHttpStatus(missing, 404), true);
	assert.equal(httpStatus(conflict), 409);
	assert.equal(isHttpStatus(conflict, 409), true);
	assert.equal(isHttpStatus(missing, 409), false);
});

test('httpStatus reads the response status when httpCode was not copied', () => {
	const error = {
		message: 'The resource you are requesting could not be found',
		response: { status: 404 },
	};
	assert.equal(httpStatus(error), 404);
});

test('httpStatus prefers the HTTP status over a non-numeric error code', () => {
	const error = {
		code: 'ERR_BAD_REQUEST',
		statusCode: 409,
		response: { status: 409 },
	};
	assert.equal(httpStatus(error), 409);
});

test('httpStatus ignores a message that only looks like a missing resource', () => {
	assert.equal(httpStatus({ message: 'could not be found' }), undefined);
	assert.equal(httpStatus({ message: 'not found', status: 'error' }), undefined);
});

test('httpStatus follows cause', () => {
	const error = { message: 'wrapped', cause: { statusCode: 404 } };
	assert.equal(httpStatus(error), 404);
});

test('apiErrorText surfaces an API error code such as https_required', () => {
	assert.equal(apiErrorText({ statusCode: 422, error: 'https_required' }), 'https_required');
	assert.equal(
		apiErrorText({ statusCode: 422, error: { error: 'https_required' } }),
		'https_required',
	);
	assert.equal(
		apiErrorText({ response: { status: 422, data: { detail: 'https_required' } } }),
		'https_required',
	);
	assert.equal(
		apiErrorText({
			statusCode: 422,
			error: { code: 'https_required', message: 'Webhooks require HTTPS' },
		}),
		'https_required: Webhooks require HTTPS',
	);
});

test('apiErrorText reads a nested detail object and a cause body', () => {
	assert.equal(
		apiErrorText({
			statusCode: 401,
			error: {
				detail: {
					code: 'auth_failed',
					message: 'The calendar server rejected the login.',
				},
			},
		}),
		'auth_failed: The calendar server rejected the login.',
	);
	assert.equal(
		apiErrorText({
			message: 'wrapped',
			cause: { statusCode: 409, error: { detail: 'Event is already in this calendar' } },
		}),
		'Event is already in this calendar',
	);
});
