import {
	NodeApiError,
	type IDataObject,
	type IExecuteFunctions,
	type IHookFunctions,
	type IHttpRequestOptions,
	type ILoadOptionsFunctions,
	type JsonObject,
} from 'n8n-workflow';

export type AnyMomentContext = IExecuteFunctions | IHookFunctions | ILoadOptionsFunctions;

export const DEFAULT_BASE_URL = 'https://api.anymoment.sineways.tech';

export function baseUrlFromCredentials(credentials: IDataObject): string {
	const raw = String(credentials.baseUrl || DEFAULT_BASE_URL).trim();
	return raw.replace(/\/+$/, '');
}

export function asArray(value: unknown): IDataObject[] {
	if (Array.isArray(value)) return value as IDataObject[];
	return [];
}

export function locatorValue(value: unknown): string {
	if (value && typeof value === 'object' && 'value' in (value as IDataObject)) {
		return String((value as IDataObject).value ?? '').trim();
	}
	return String(value ?? '').trim();
}

export function headerValue(
	headers: Record<string, string | string[] | undefined>,
	name: string,
): string {
	const value = headers[name] ?? headers[name.toLowerCase()];
	if (Array.isArray(value)) return String(value[0] ?? '');
	return String(value ?? '');
}

function cleanQuery(qs?: IDataObject): IDataObject | undefined {
	if (!qs) return undefined;
	const query: IDataObject = {};
	for (const [key, value] of Object.entries(qs)) {
		if (value === undefined || value === null || value === '') continue;
		query[key] = value;
	}
	return Object.keys(query).length ? query : undefined;
}

function isEmptyDeleteResponse(error: unknown): boolean {
	const message = error instanceof Error ? error.message : String(error ?? '');
	return /unexpected end|JSON|empty|204/i.test(message);
}

export async function anyMomentApiRequest(
	context: AnyMomentContext,
	method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE',
	path: string,
	body?: IDataObject,
	qs?: IDataObject,
): Promise<IDataObject | IDataObject[]> {
	const credentials = await context.getCredentials('anyMomentApi');
	const options: IHttpRequestOptions = {
		method,
		url: `${baseUrlFromCredentials(credentials)}${path}`,
		qs: cleanQuery(qs),
		json: true,
		headers: {
			Accept: 'application/json',
		},
	};
	if (body !== undefined && method !== 'GET' && method !== 'DELETE') {
		const emptyObject =
			typeof body === 'object' &&
			body !== null &&
			!Array.isArray(body) &&
			Object.keys(body).length === 0;
		// n8n omits an empty object, but POST /calendars/{id}/events/{id} requires a JSON body. {} is valid.
		options.body = emptyObject ? '{}' : body;
		options.headers = {
			...options.headers,
			'Content-Type': 'application/json',
		};
	}

	try {
		const response = await context.helpers.httpRequestWithAuthentication.call(
			context,
			'anyMomentApi',
			options,
		);
		if (response === undefined || response === null || response === '') {
			return { success: true };
		}
		return response as IDataObject | IDataObject[];
	} catch (error) {
		if (method === 'DELETE' && isEmptyDeleteResponse(error)) {
			return { success: true };
		}
		throw new NodeApiError(context.getNode(), error as JsonObject);
	}
}

export function errorText(error: unknown): string {
	if (error instanceof Error) return error.message;
	return String(error ?? '');
}
