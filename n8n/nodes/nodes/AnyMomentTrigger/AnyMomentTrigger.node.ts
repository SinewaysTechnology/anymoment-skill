import {
	NodeApiError,
	NodeConnectionTypes,
	NodeOperationError,
	type IDataObject,
	type IHookFunctions,
	type INodeType,
	type INodeTypeDescription,
	type IWebhookFunctions,
	type IWebhookResponseData,
	type JsonObject,
} from 'n8n-workflow';

import {
	anyMomentApiRequest,
	asArray,
	errorText,
	headerValue,
	isHttpStatus,
	locatorValue,
} from '../shared/api';
import { businessDayFields, calendarLocator, eventLocator } from '../shared/fields';
import { buildRuleBody, readBusinessDayInput } from '../shared/rule';
import { verifyAnyMomentSignature } from '../shared/signature';

const CREATE_RULE = { ruleMode: ['create'] };
const EXISTING_RULE = { ruleMode: ['existing'] };

type StaticData = {
	subscriptionId?: string;
	eventId?: string;
	calendarId?: string;
	secret?: string;
	createdEvent?: boolean;
	webhookUrl?: string;
};

function staticData(context: IHookFunctions): StaticData {
	return context.getWorkflowStaticData('node') as StaticData;
}

function rawBodyOf(request: {
	rawBody?: Buffer | string;
	body?: unknown;
}): string {
	if (typeof request.rawBody === 'string') return request.rawBody;
	if (request.rawBody && Buffer.isBuffer(request.rawBody)) return request.rawBody.toString('utf8');
	return '';
}

async function ensureRule(
	context: IHookFunctions,
	calendarId: string,
): Promise<{ eventId: string; created: boolean }> {
	const data = staticData(context);
	const ruleMode = context.getNodeParameter('ruleMode') as string;
	if (ruleMode === 'existing') {
		const eventId = locatorValue(context.getNodeParameter('eventId'));
		if (!eventId) {
			throw new NodeOperationError(context.getNode(), 'Choose the AnyMoment rule to subscribe.');
		}
		data.createdEvent = false;
		data.eventId = eventId;
		return { eventId, created: false };
	}

	let body: IDataObject;
	try {
		body = buildRuleBody(
			readBusinessDayInput((name, fallback) => context.getNodeParameter(name, fallback)),
		);
	} catch (error) {
		throw new NodeOperationError(context.getNode(), error as Error);
	}

	let eventId = data.createdEvent ? data.eventId : undefined;
	let created = false;
	if (eventId) {
		try {
			await anyMomentApiRequest(context, 'GET', `/events/${eventId}`);
			await anyMomentApiRequest(context, 'PUT', `/events/${eventId}`, body);
		} catch (error) {
			if (!isHttpStatus(error, 404)) {
				throw new NodeApiError(context.getNode(), error as JsonObject);
			}
			eventId = undefined;
		}
	}
	if (!eventId) {
		const createdEvent = (await anyMomentApiRequest(
			context,
			'POST',
			'/events',
			body,
		)) as IDataObject;
		eventId = String(createdEvent.id || '');
		if (!eventId) {
			throw new NodeOperationError(context.getNode(), 'AnyMoment did not return an event id.');
		}
		data.createdEvent = true;
		created = true;
	}
	data.eventId = eventId;

	try {
		await anyMomentApiRequest(context, 'POST', `/calendars/${calendarId}/events/${eventId}`, {});
	} catch (error) {
		if (!isHttpStatus(error, 409)) {
			throw new NodeApiError(context.getNode(), error as JsonObject);
		}
	}
	return { eventId, created };
}

export class AnyMomentTrigger implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'AnyMoment Trigger',
		name: 'anyMomentTrigger',
		icon: { light: 'file:anymoment.svg', dark: 'file:anymoment.dark.svg' },
		group: ['trigger'],
		version: 1,
		subtitle: 'occurrence.due',
		description:
			'Starts a workflow when AnyMoment sends occurrence.due for a business-day rule',
		defaults: {
			name: 'AnyMoment Trigger',
		},
		inputs: [],
		outputs: [NodeConnectionTypes.Main],
		credentials: [
			{
				name: 'anyMomentApi',
				required: true,
			},
		],
		webhooks: [
			{
				name: 'default',
				httpMethod: 'POST',
				responseMode: 'onReceived',
				// An empty responseData lets webhookResponse through. The default "firstEntryJson"
				// is sent as the literal body and ignores webhookResponse.
				responseData: '' as 'noData',
				path: 'webhook',
			},
		],
		properties: [
			{
				displayName:
					'Outgoing webhooks need Pro after the free 30-day trial. Create the calendar in AnyMoment first. Get an API key at https://anymoment.sineways.tech/?ref=n8n-node. The key needs events:read, events:write, calendars:read, and webhooks:manage.',
				name: 'trialNotice',
				type: 'notice',
				default: '',
			},
			calendarLocator({}),
			{
				displayName: 'Rule Source',
				name: 'ruleMode',
				type: 'options',
				default: 'create',
				noDataExpression: true,
				description: 'Create a monthly business-day rule on activate, or subscribe an existing rule',
				options: [
					{
						name: 'Create From Fields',
						value: 'create',
						description: 'Create or update a monthly rule from the fields below, then subscribe',
					},
					{
						name: 'Existing Rule',
						value: 'existing',
						description: 'Subscribe a rule that already exists',
					},
				],
			},
			eventLocator(
				EXISTING_RULE,
				'Existing AnyMoment rule to watch. From List calls GET /events, which a calendar-limited API key cannot call. Use By ID in that case.',
			),
			...businessDayFields(CREATE_RULE),
			{
				displayName: 'Occurrence Offset (Seconds)',
				name: 'occurrenceOffsetSeconds',
				type: 'number',
				default: 0,
				typeOptions: { numberPrecision: 0 },
				description:
					'Seconds added to the occurrence time before AnyMoment sends the webhook. A negative value sends the call early. 0 sends at the occurrence. The API source caps this at 7 days either way. The OpenAPI schema does not declare that bound.',
			},
			{
				displayName: 'Timestamp Window (Seconds)',
				name: 'timestampToleranceSeconds',
				type: 'number',
				default: 300,
				typeOptions: { minValue: 0, numberPrecision: 0 },
				description:
					'Reject a delivery when X-AnyMoment-Timestamp is further than this many seconds from now. 300 matches the published verification example. Set to 0 to check the signature only. The OpenAPI schema does not document this window.',
			},
		],
	};

	webhookMethods = {
		default: {
			async checkExists(this: IHookFunctions): Promise<boolean> {
				const calendarId = locatorValue(this.getNodeParameter('calendarId'));
				const webhookUrl = this.getNodeWebhookUrl('default');
				if (!calendarId || !webhookUrl) return false;
				const response = await anyMomentApiRequest(
					this,
					'GET',
					`/calendars/${calendarId}/subscriptions`,
				);
				const match = asArray(response).find((subscription) => {
					const types = Array.isArray(subscription.event_types) ? subscription.event_types : [];
					return subscription.url === webhookUrl && types.includes('occurrence.due');
				});
				if (!match) return false;
				const data = staticData(this);
				data.subscriptionId = String(match.id);
				data.calendarId = calendarId;
				data.webhookUrl = webhookUrl;
				return true;
			},
			async create(this: IHookFunctions): Promise<boolean> {
				const calendarId = locatorValue(this.getNodeParameter('calendarId'));
				const webhookUrl = this.getNodeWebhookUrl('default');
				if (!calendarId) {
					throw new NodeOperationError(this.getNode(), 'Choose a calendar.');
				}
				if (!webhookUrl) {
					throw new NodeOperationError(this.getNode(), 'n8n did not provide a webhook URL.');
				}
				const prepared = await ensureRule(this, calendarId);
				const credentials = await this.getCredentials('anyMomentApi');
				const suppliedSecret = String(credentials.webhookSecret || '').trim();
				const offset = Number(this.getNodeParameter('occurrenceOffsetSeconds', 0));
				const payload: IDataObject = {
					url: webhookUrl,
					event_types: ['occurrence.due'],
					occurrence_offset_seconds: Number.isFinite(offset) ? offset : 0,
				};
				if (suppliedSecret) payload.secret = suppliedSecret;
				let created: IDataObject;
				try {
					created = (await anyMomentApiRequest(
						this,
						'POST',
						`/calendars/${calendarId}/subscriptions`,
						payload,
					)) as IDataObject;
				} catch (error) {
					if (prepared.created) {
						try {
							await anyMomentApiRequest(this, 'DELETE', `/events/${prepared.eventId}`);
							const orphaned = staticData(this);
							orphaned.createdEvent = false;
							delete orphaned.eventId;
						} catch (cleanupError) {
							throw new NodeApiError(this.getNode(), cleanupError as JsonObject, {
								message: `${errorText(error)} The new rule was left in place because deleting it failed.`,
							});
						}
					}
					throw new NodeApiError(this.getNode(), error as JsonObject);
				}
				const data = staticData(this);
				data.subscriptionId = String(created.id || '');
				data.eventId = prepared.eventId;
				data.calendarId = calendarId;
				data.webhookUrl = webhookUrl;
				data.secret = suppliedSecret || String(created.secret || '');
				if (!data.subscriptionId) {
					throw new NodeOperationError(
						this.getNode(),
						'AnyMoment did not return a subscription id.',
					);
				}
				return true;
			},
			async delete(this: IHookFunctions): Promise<boolean> {
				const data = staticData(this);
				const calendarId = data.calendarId || locatorValue(this.getNodeParameter('calendarId'));
				const subscriptionId = data.subscriptionId;
				if (calendarId && subscriptionId) {
					try {
						await anyMomentApiRequest(
							this,
							'DELETE',
							`/calendars/${calendarId}/subscriptions/${subscriptionId}`,
						);
					} catch (error) {
						if (!isHttpStatus(error, 404)) {
							throw new NodeApiError(this.getNode(), error as JsonObject);
						}
					}
				}
				delete data.subscriptionId;
				return true;
			},
		},
	};

	async webhook(this: IWebhookFunctions): Promise<IWebhookResponseData> {
		const request = this.getRequestObject() as {
			headers: Record<string, string | string[] | undefined>;
			rawBody?: Buffer | string;
			body?: unknown;
		};
		const rawBody = rawBodyOf(request);
		const credentials = await this.getCredentials('anyMomentApi');
		const data = this.getWorkflowStaticData('node') as StaticData;
		const secret = String(credentials.webhookSecret || data.secret || '');
		const tolerance = Number(this.getNodeParameter('timestampToleranceSeconds', 300));
		const check = await verifyAnyMomentSignature({
			secret,
			timestamp: headerValue(request.headers, 'x-anymoment-timestamp'),
			rawBody,
			signature: headerValue(request.headers, 'x-anymoment-signature'),
			toleranceSeconds: Number.isFinite(tolerance) ? tolerance : 300,
		});
		if (!rawBody) {
			check.ok = false;
			check.reason = 'The raw request body is missing, so the signature cannot be checked.';
		}
		if (!check.ok) {
			const response = this.getResponseObject();
			response.status(401).json({ ok: false, error: check.reason });
			return { noWebhookResponse: true };
		}
		let payload: IDataObject = {};
		try {
			payload = JSON.parse(rawBody) as IDataObject;
		} catch {
			payload = {};
		}
		return {
			webhookResponse: { ok: true },
			workflowData: [
				[
					{
						json: {
							...payload,
							deliveryId: headerValue(request.headers, 'x-anymoment-delivery'),
							signatureValid: true,
						},
					},
				],
			],
		};
	}
}
