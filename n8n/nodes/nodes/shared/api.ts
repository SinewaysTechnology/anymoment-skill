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

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function numericStatus(value: unknown): number | undefined {
	if (typeof value === 'number' && value >= 100 && value <= 599) return value;
	if (typeof value === 'string' && /^\d{3}$/.test(value)) {
		const parsed = Number(value);
		if (parsed >= 100 && parsed <= 599) return parsed;
	}
	return undefined;
}

// NodeApiError.message is a generic status sentence. The HTTP status lives on
// httpCode, and the request helper also sets statusCode and response.status.
export function httpStatus(error: unknown): number | undefined {
	if (!isRecord(error)) return undefined;
	const response = isRecord(error.response) ? error.response : undefined;
	const candidates = [
		error.httpCode,
		error.statusCode,
		response?.status,
		response?.statusCode,
		error.status,
	];
	for (const candidate of candidates) {
		const status = numericStatus(candidate);
		if (status !== undefined) return status;
	}
	if (error.cause && error.cause !== error) return httpStatus(error.cause);
	return undefined;
}

export function isHttpStatus(error: unknown, status: number): boolean {
	return httpStatus(error) === status;
}

function responseBody(error: unknown): unknown {
	if (!isRecord(error)) return undefined;
	if (error.error !== undefined && !(error.error instanceof Error)) return error.error;
	const response = isRecord(error.response) ? error.response : undefined;
	if (response) {
		if (response.data !== undefined) return response.data;
		if (response.body !== undefined) return response.body;
	}
	if (error.cause && error.cause !== error) return responseBody(error.cause);
	return undefined;
}

function stringField(record: Record<string, unknown>, key: string): string {
	const value = record[key];
	return typeof value === 'string' ? value.trim() : '';
}

function describeBody(body: unknown, depth = 0): string {
	if (depth > 4) return '';
	if (typeof body === 'string') {
		const trimmed = body.trim();
		if (!trimmed) return '';
		if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
			try {
				const described = describeBody(JSON.parse(trimmed) as unknown, depth + 1);
				if (described) return described;
			} catch {
				return trimmed;
			}
		}
		return trimmed;
	}
	if (Array.isArray(body)) {
		return body
			.map((item) => describeBody(item, depth + 1))
			.filter(Boolean)
			.join('; ');
	}
	if (!isRecord(body)) return '';

	const nestedError =
		body.error !== undefined && typeof body.error !== 'string'
			? describeBody(body.error, depth + 1)
			: '';
	const nestedDetail =
		body.detail !== undefined && typeof body.detail !== 'string'
			? describeBody(body.detail, depth + 1)
			: '';
	const code = stringField(body, 'code') || stringField(body, 'error_code');
	const errorString = stringField(body, 'error');
	const message =
		stringField(body, 'user_message') ||
		stringField(body, 'message') ||
		stringField(body, 'msg') ||
		stringField(body, 'detail') ||
		stringField(body, 'error_description') ||
		stringField(body, 'title');
	const codePart = code || (errorString && /^[A-Za-z0-9_]+$/.test(errorString) ? errorString : '');
	const messagePart =
		message ||
		(errorString && errorString !== codePart ? errorString : '') ||
		nestedError ||
		nestedDetail;
	if (codePart && messagePart && codePart !== messagePart) return `${codePart}: ${messagePart}`;
	return codePart || messagePart;
}

export function apiErrorText(error: unknown): string {
	return describeBody(responseBody(error));
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
		const status = httpStatus(error);
		const detail = apiErrorText(error);
		throw new NodeApiError(context.getNode(), error as JsonObject, {
			message: detail || undefined,
			httpCode: status !== undefined ? String(status) : undefined,
		});
	}
}

export function errorText(error: unknown): string {
	if (error instanceof Error) return error.message;
	return String(error ?? '');
}
