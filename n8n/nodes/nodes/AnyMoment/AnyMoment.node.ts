import {
	NodeApiError,
	NodeConnectionTypes,
	NodeOperationError,
	type IDataObject,
	type IExecuteFunctions,
	type ILoadOptionsFunctions,
	type INodeExecutionData,
	type INodeListSearchResult,
	type INodeType,
	type INodeTypeDescription,
	type JsonObject,
} from 'n8n-workflow';

import { anyMomentApiRequest, asArray, errorText, locatorValue } from '../shared/api';
import { businessDayFields, calendarLocator, eventLocator } from '../shared/fields';
import { buildRuleBody, readBusinessDayInput } from '../shared/rule';

const RULE = { resource: ['rule'] };
const SUBSCRIPTION = { resource: ['subscription'] };

const EVENT_TYPE_OPTIONS = [
	{ name: 'Event Created', value: 'event.created' },
	{ name: 'Event Deleted', value: 'event.deleted' },
	{ name: 'Event Updated', value: 'event.updated' },
	{
		name: 'Occurrence Due',
		value: 'occurrence.due',
		description: 'Fires when a rule occurrence is due',
	},
];

async function searchRecords(
	context: ILoadOptionsFunctions,
	path: string,
	filter: string | undefined,
	label: (row: IDataObject) => string,
): Promise<INodeListSearchResult> {
	const response = await anyMomentApiRequest(context, 'GET', path);
	const query = (filter || '').toLowerCase();
	const results = asArray(response)
		.filter((row) => {
			const name = label(row).toLowerCase();
			const id = String(row.id || '');
			return !query || name.includes(query) || id.includes(query);
		})
		.map((row) => ({
			name: label(row),
			value: String(row.id),
		}));
	return { results };
}

function requireId(value: string, label: string, itemIndex: number, node: IExecuteFunctions): string {
	if (!value) {
		throw new NodeOperationError(node.getNode(), `${label} is required.`, { itemIndex });
	}
	return value;
}

async function runRule(
	context: IExecuteFunctions,
	operation: string,
	itemIndex: number,
): Promise<IDataObject | IDataObject[]> {
	if (operation === 'create') {
		let body: IDataObject;
		try {
			body = buildRuleBody(
				readBusinessDayInput((name, fallback) => context.getNodeParameter(name, itemIndex, fallback)),
			);
		} catch (error) {
			throw new NodeOperationError(context.getNode(), error as Error, { itemIndex });
		}
		const created = (await anyMomentApiRequest(context, 'POST', '/events', body)) as IDataObject;
		const calendarId = locatorValue(context.getNodeParameter('linkCalendarId', itemIndex, ''));
		if (calendarId && created.id) {
			const link = (await anyMomentApiRequest(
				context,
				'POST',
				`/calendars/${calendarId}/events/${created.id}`,
				{},
			)) as IDataObject;
			created.calendar_link = link;
		}
		return created;
	}

	const eventId = requireId(
		locatorValue(context.getNodeParameter('eventId', itemIndex)),
		'Rule',
		itemIndex,
		context,
	);

	if (operation === 'get') {
		return (await anyMomentApiRequest(context, 'GET', `/events/${eventId}`)) as IDataObject;
	}
	if (operation === 'delete') {
		await anyMomentApiRequest(context, 'DELETE', `/events/${eventId}`);
		return { success: true, id: eventId };
	}
	if (operation === 'getAll') {
		const active = String(context.getNodeParameter('isActive', itemIndex, ''));
		const query: IDataObject = {
			minimal: context.getNodeParameter('minimal', itemIndex, true) as boolean,
			limit: context.getNodeParameter('limit', itemIndex, 50) as number,
			offset: context.getNodeParameter('offset', itemIndex, 0) as number,
		};
		if (active === 'true') query.is_active = true;
		if (active === 'false') query.is_active = false;
		const response = await anyMomentApiRequest(context, 'GET', '/events', undefined, query);
		return asArray(response);
	}
	if (operation === 'nextInstance') {
		return (await anyMomentApiRequest(
			context,
			'GET',
			`/events/${eventId}/next-instance`,
		)) as IDataObject;
	}
	if (operation === 'preview') {
		const count = Number(context.getNodeParameter('count', itemIndex, 6));
		const months = Number(context.getNodeParameter('lookAheadMonths', itemIndex, 18));
		const start = new Date();
		const end = new Date(start.getTime());
		end.setUTCMonth(end.getUTCMonth() + (Number.isFinite(months) && months > 0 ? months : 18));
		const response = (await anyMomentApiRequest(context, 'GET', `/events/${eventId}/instances`, undefined, {
			start: start.toISOString(),
			end: end.toISOString(),
			optimized: true,
			include_webhooks: false,
			format: 'json',
		})) as IDataObject;
		const instances = Array.isArray(response.instances) ? (response.instances as IDataObject[]) : [];
		const limited = instances.slice(0, Number.isFinite(count) && count > 0 ? count : instances.length);
		const eventRecord = response.event as IDataObject | undefined;
		const resolvedEventId = String(response.event_id || eventRecord?.id || eventId);
		if (!limited.length) {
			return [
				{
					eventId: resolvedEventId,
					instances: [],
					message: 'No occurrences in the look-ahead window. Increase Look Ahead (Months).',
				},
			];
		}
		return limited.map((instance) => ({
			eventId: resolvedEventId,
			...instance,
		}));
	}
	throw new NodeOperationError(context.getNode(), `Unknown rule operation: ${operation}`, {
		itemIndex,
	});
}

async function runSubscription(
	context: IExecuteFunctions,
	operation: string,
	itemIndex: number,
): Promise<IDataObject | IDataObject[]> {
	const calendarId = requireId(
		locatorValue(context.getNodeParameter('calendarId', itemIndex)),
		'Calendar',
		itemIndex,
		context,
	);
	if (operation === 'getAll') {
		const response = await anyMomentApiRequest(
			context,
			'GET',
			`/calendars/${calendarId}/subscriptions`,
		);
		return asArray(response);
	}
	if (operation === 'create') {
		const url = String(context.getNodeParameter('url', itemIndex, '')).trim();
		if (!url) {
			throw new NodeOperationError(context.getNode(), 'Subscription URL is required.', { itemIndex });
		}
		const eventTypes = context.getNodeParameter('eventTypes', itemIndex, ['occurrence.due']) as string[];
		if (!eventTypes.length) {
			throw new NodeOperationError(context.getNode(), 'Choose at least one event type.', { itemIndex });
		}
		const body: IDataObject = {
			url,
			event_types: eventTypes,
			occurrence_offset_seconds: Number(context.getNodeParameter('occurrenceOffsetSeconds', itemIndex, 0)),
		};
		const secret = String(context.getNodeParameter('signingSecret', itemIndex, '')).trim();
		if (secret) body.secret = secret;
		return (await anyMomentApiRequest(
			context,
			'POST',
			`/calendars/${calendarId}/subscriptions`,
			body,
		)) as IDataObject;
	}

	const subscriptionId = requireId(
		String(context.getNodeParameter('subscriptionId', itemIndex, '')).trim(),
		'Subscription',
		itemIndex,
		context,
	);
	const base = `/calendars/${calendarId}/subscriptions/${subscriptionId}`;
	if (operation === 'get') {
		return (await anyMomentApiRequest(context, 'GET', base)) as IDataObject;
	}
	if (operation === 'delete') {
		await anyMomentApiRequest(context, 'DELETE', base);
		return { success: true, id: subscriptionId, calendarId };
	}
	if (operation === 'listDeliveries') {
		const response = await anyMomentApiRequest(context, 'GET', `${base}/deliveries`, undefined, {
			limit: context.getNodeParameter('deliveryLimit', itemIndex, 50) as number,
		});
		return asArray(response);
	}
	if (operation === 'replay') {
		const deliveryId = requireId(
			String(context.getNodeParameter('deliveryId', itemIndex, '')).trim(),
			'Delivery',
			itemIndex,
			context,
		);
		return (await anyMomentApiRequest(
			context,
			'POST',
			`${base}/deliveries/${deliveryId}/replay`,
			{},
		)) as IDataObject;
	}
	throw new NodeOperationError(context.getNode(), `Unknown subscription operation: ${operation}`, {
		itemIndex,
	});
}

export class AnyMoment implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'AnyMoment',
		name: 'anyMoment',
		icon: { light: 'file:anymoment.svg', dark: 'file:anymoment.dark.svg' },
		group: ['transform'],
		version: 1,
		subtitle: '={{$parameter["resource"] + ": " + $parameter["operation"]}}',
		description: 'Create business-day rules, preview their dates, and manage webhook subscriptions',
		defaults: {
			name: 'AnyMoment',
		},
		inputs: [NodeConnectionTypes.Main],
		outputs: [NodeConnectionTypes.Main],
		usableAsTool: true,
		credentials: [
			{
				name: 'anyMomentApi',
				required: true,
			},
		],
		properties: [
			{
				displayName: 'Resource',
				name: 'resource',
				type: 'options',
				noDataExpression: true,
				default: 'rule',
				options: [
					{ name: 'Rule', value: 'rule', description: 'A recurrent event, including business-day rules' },
					{
						name: 'Subscription',
						value: 'subscription',
						description: 'An outgoing calendar webhook subscription',
					},
				],
			},
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				default: 'preview',
				displayOptions: { show: RULE },
				options: [
					{
						name: 'Create',
						value: 'create',
						action: 'Create a business day rule',
						description: 'Create a monthly rule from structured fields',
					},
					{ name: 'Delete', value: 'delete', action: 'Delete a rule', description: 'Delete a rule' },
					{ name: 'Get', value: 'get', action: 'Get a rule', description: 'Get one rule' },
					{
						name: 'Get Many',
						value: 'getAll',
						action: 'Get many rules',
						description: 'List rules for this account',
					},
					{
						name: 'Get Next Instance',
						value: 'nextInstance',
						action: 'Get the next date',
						description: 'Get the next occurrence of a saved rule',
					},
					{
						name: 'Preview Next Dates',
						value: 'preview',
						action: 'Preview the next dates',
						description:
							'Return the next dates of a saved rule. The API has no unsaved structured preview, so this calls instances and keeps the first N.',
					},
				],
			},
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				default: 'getAll',
				displayOptions: { show: SUBSCRIPTION },
				options: [
					{
						name: 'Create',
						value: 'create',
						action: 'Create a subscription',
						description: 'Subscribe a URL to calendar events',
					},
					{
						name: 'Delete',
						value: 'delete',
						action: 'Delete a subscription',
						description: 'Delete a subscription',
					},
					{
						name: 'Get',
						value: 'get',
						action: 'Get a subscription',
						description: 'Get one subscription. The secret is not included.',
					},
					{
						name: 'Get Many',
						value: 'getAll',
						action: 'Get many subscriptions',
						description: 'List subscriptions on a calendar. Secrets are not included.',
					},
					{
						name: 'Get Many Deliveries',
						value: 'listDeliveries',
						action: 'List deliveries',
						description: 'List delivery attempts for one subscription, newest first',
					},
					{
						name: 'Replay Delivery',
						value: 'replay',
						action: 'Replay a delivery',
						description: 'Queue a new delivery with the same payload',
					},
				],
			},
			calendarLocator({
				resource: ['subscription'],
			}),
			{
				...calendarLocator({ resource: ['rule'], operation: ['create'] }),
				displayName: 'Add to Calendar',
				name: 'linkCalendarId',
				required: false,
				description:
					'Optional calendar to attach the new rule to. Leave empty to create the rule without a calendar. Linking is what makes occurrence.due fire.',
			},
			eventLocator(
				{ resource: ['rule'], operation: ['get', 'delete', 'preview', 'nextInstance'] },
				'Rule to read. From List calls GET /events. A key limited to specific calendars cannot call that route, so use By ID.',
			),
			...businessDayFields({ resource: ['rule'], operation: ['create'] }),
			{
				displayName: 'How Many Dates',
				name: 'count',
				type: 'number',
				default: 6,
				typeOptions: { minValue: 1, maxValue: 100, numberPrecision: 0 },
				description:
					'Maximum number of dates to return. The instances endpoint has no N parameter, so extra dates in the window are dropped here.',
				displayOptions: { show: { resource: ['rule'], operation: ['preview'] } },
			},
			{
				displayName: 'Look Ahead (Months)',
				name: 'lookAheadMonths',
				type: 'number',
				default: 18,
				typeOptions: { minValue: 1, maxValue: 120, numberPrecision: 0 },
				description: 'How far ahead to ask GET /events/{ID}/instances. The call needs a start and an end. There is no endpoint that previews a structured rule without saving it.',
				displayOptions: { show: { resource: ['rule'], operation: ['preview'] } },
			},
			{
				displayName: 'Active',
				name: 'isActive',
				type: 'options',
				default: '',
				description: 'Filter the rule list by active status. Any means do not send the filter.',
				displayOptions: { show: { resource: ['rule'], operation: ['getAll'] } },
				options: [
					{ name: 'Any', value: '' },
					{ name: 'Active', value: 'true' },
					{ name: 'Inactive', value: 'false' },
				],
			},
			{
				displayName: 'Minimal',
				name: 'minimal',
				type: 'boolean',
				default: true,
				description: 'Whether to return minimal rule data, which is faster for listings',
				displayOptions: { show: { resource: ['rule'], operation: ['getAll'] } },
			},
			{
				displayName: 'Limit',
				name: 'limit',
				type: 'number',
				default: 50,
				typeOptions: { minValue: 1, numberPrecision: 0 },
				description: 'Max number of results to return',
				displayOptions: { show: { resource: ['rule'], operation: ['getAll'] } },
			},
			{
				displayName: 'Offset',
				name: 'offset',
				type: 'number',
				default: 0,
				typeOptions: { minValue: 0, numberPrecision: 0 },
				description: 'Number of rules to skip',
				displayOptions: { show: { resource: ['rule'], operation: ['getAll'] } },
			},
			{
				displayName: 'URL',
				name: 'url',
				type: 'string',
				default: '',
				placeholder: 'https://example.com/hooks/anymoment',
				required: true,
				description: 'HTTPS URL that receives the webhook. AnyMoment rejects plain HTTP and private hosts.',
				displayOptions: { show: { resource: ['subscription'], operation: ['create'] } },
			},
			{
				displayName: 'Event Types',
				name: 'eventTypes',
				type: 'multiOptions',
				default: ['occurrence.due'],
				description:
					'Change types to deliver. The OpenAPI schema types this as an open string array and does not list the values. These four are the types the API sends.',
				displayOptions: { show: { resource: ['subscription'], operation: ['create'] } },
				options: EVENT_TYPE_OPTIONS,
			},
			{
				displayName: 'Occurrence Offset (Seconds)',
				name: 'occurrenceOffsetSeconds',
				type: 'number',
				default: 0,
				typeOptions: { numberPrecision: 0 },
				description:
					'Seconds added to the occurrence time before delivery. A negative value sends the call early.',
				displayOptions: { show: { resource: ['subscription'], operation: ['create'] } },
			},
			{
				displayName: 'Signing Secret',
				name: 'signingSecret',
				type: 'string',
				typeOptions: { password: true },
				default: '',
				description:
					'Optional secret you choose. AnyMoment stores it and does not return it. Leave empty and the create response includes a generated secret once.',
				displayOptions: { show: { resource: ['subscription'], operation: ['create'] } },
			},
			{
				displayName: 'Subscription ID',
				name: 'subscriptionId',
				type: 'string',
				default: '',
				required: true,
				description: 'Subscription ID returned when the subscription was created',
				displayOptions: {
					show: {
						resource: ['subscription'],
						operation: ['get', 'delete', 'listDeliveries', 'replay'],
					},
				},
			},
			{
				displayName: 'Delivery Limit',
				name: 'deliveryLimit',
				type: 'number',
				default: 50,
				typeOptions: { minValue: 1, maxValue: 200, numberPrecision: 0 },
				description: 'How many deliveries to return. The API allows 1 to 200 and defaults to 50.',
				displayOptions: { show: { resource: ['subscription'], operation: ['listDeliveries'] } },
			},
			{
				displayName: 'Delivery ID',
				name: 'deliveryId',
				type: 'string',
				default: '',
				required: true,
				description: 'Delivery ID to replay. The original row is left unchanged.',
				displayOptions: { show: { resource: ['subscription'], operation: ['replay'] } },
			},
		],
	};

	methods = {
		listSearch: {
			async searchCalendars(
				this: ILoadOptionsFunctions,
				filter?: string,
			): Promise<INodeListSearchResult> {
				return searchRecords(this, '/calendars?limit=100', filter, (row) =>
					String(row.name || row.id),
				);
			},
			async searchEvents(this: ILoadOptionsFunctions, filter?: string): Promise<INodeListSearchResult> {
				return searchRecords(this, '/events?minimal=true&limit=100', filter, (row) =>
					String(row.name || row.id),
				);
			},
		},
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];
		for (let itemIndex = 0; itemIndex < items.length; itemIndex++) {
			try {
				const resource = this.getNodeParameter('resource', itemIndex) as string;
				const operation = this.getNodeParameter('operation', itemIndex) as string;
				const result =
					resource === 'subscription'
						? await runSubscription(this, operation, itemIndex)
						: await runRule(this, operation, itemIndex);
				const rows = Array.isArray(result) ? result : [result];
				if (!rows.length) {
					returnData.push({ json: {}, pairedItem: { item: itemIndex } });
					continue;
				}
				for (const row of rows) {
					returnData.push({ json: row, pairedItem: { item: itemIndex } });
				}
			} catch (error) {
				if (this.continueOnFail()) {
					returnData.push({
						json: { error: errorText(error) },
						pairedItem: { item: itemIndex },
					});
					continue;
				}
				if (error instanceof NodeOperationError) {
					throw new NodeOperationError(this.getNode(), error.message, { itemIndex });
				}
				throw new NodeApiError(this.getNode(), error as JsonObject, { itemIndex });
			}
		}
		return [returnData];
	}
}
