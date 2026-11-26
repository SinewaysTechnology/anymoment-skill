import type {
	IAuthenticateGeneric,
	ICredentialTestRequest,
	ICredentialType,
	INodeProperties,
} from 'n8n-workflow';

export class AnyMomentApi implements ICredentialType {
	name = 'anyMomentApi';

	displayName = 'AnyMoment API';

	icon = { light: 'file:anymoment.svg', dark: 'file:anymoment.dark.svg' } as const;

	documentationUrl = 'https://anymoment.sineways.tech/?ref=n8n-node';

	properties: INodeProperties[] = [
		{
			displayName: 'API Key',
			name: 'apiKey',
			type: 'string',
			typeOptions: { password: true },
			default: '',
			required: true,
			description:
				'API key from AnyMoment settings. Get an API key at https://anymoment.sineways.tech/?ref=n8n-node. Sent as Authorization: Bearer. The credential test calls GET /calendars and needs calendars:read. Rules need events:read and events:write. The trigger needs webhooks:manage as well.',
		},
		{
			displayName: 'Webhook Signing Secret',
			name: 'webhookSecret',
			type: 'string',
			typeOptions: { password: true },
			default: '',
			description:
				'Optional signing secret for occurrence.due deliveries. Use the secret AnyMoment returned when the subscription was created, or choose one (the service stores a caller-supplied secret and does not return it). Leave empty to let AnyMoment generate a secret when the trigger registers the subscription. That generated secret is kept in workflow static data.',
		},
		{
			displayName: 'Base URL',
			name: 'baseUrl',
			type: 'string',
			default: 'https://api.anymoment.sineways.tech',
			placeholder: 'https://api.anymoment.sineways.tech',
			description:
				'AnyMoment API origin, with no trailing slash. Keep the default for the hosted API.',
		},
	];

	authenticate: IAuthenticateGeneric = {
		type: 'generic',
		properties: {
			headers: {
				Authorization: '=Bearer {{$credentials.apiKey}}',
			},
		},
	};

	test: ICredentialTestRequest = {
		request: {
			baseURL: '={{$credentials.baseUrl}}',
			url: '/calendars',
			method: 'GET',
			qs: {
				limit: 1,
			},
		},
	};
}
