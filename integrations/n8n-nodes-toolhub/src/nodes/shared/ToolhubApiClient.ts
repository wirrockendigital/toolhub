import type { IExecuteFunctions, IDataObject } from 'n8n-workflow';
import { NodeOperationError } from 'n8n-workflow';

export interface ToolhubCredentialData extends IDataObject {
	baseUrl: string;
	apiKey?: string;
	authHeaderName?: string;
	authScheme?: 'bearer' | 'token' | 'raw';
}

export function getToolhubCredentials(context: IExecuteFunctions): ToolhubCredentialData {
	// Credentials are required by every Toolhub community node call.
	return context.getCredentials('toolhubApi') as unknown as ToolhubCredentialData;
}

export function normalizeBaseUrl(rawBaseUrl: string): string {
	// A normalized base URL prevents double slashes in joined endpoint URLs.
	return rawBaseUrl.trim().replace(/\/+$/, '');
}

export function buildAuthHeaders(credentials: ToolhubCredentialData): IDataObject {
	const headers: IDataObject = {};

	// Keep auth optional so self-hosted instances can start without API keys.
	if (!credentials.apiKey || credentials.apiKey.trim() === '') {
		return headers;
	}

	const headerName = (credentials.authHeaderName || 'Authorization').trim();
	const scheme = credentials.authScheme || 'bearer';
	const keyValue = credentials.apiKey.trim();

	if (scheme === 'raw') {
		headers[headerName] = keyValue;
	} else if (scheme === 'token') {
		headers[headerName] = `Token ${keyValue}`;
	} else {
		headers[headerName] = `Bearer ${keyValue}`;
	}

	return headers;
}

export function buildToolhubUrl(baseUrl: string, endpointPath: string): string {
	// Endpoint joining is centralized to avoid path bugs across nodes.
	const normalizedBase = normalizeBaseUrl(baseUrl);
	const normalizedPath = endpointPath.startsWith('/') ? endpointPath : `/${endpointPath}`;
	return `${normalizedBase}${normalizedPath}`;
}

export async function requestToolhubJson(
	context: IExecuteFunctions,
	options: {
		url: string;
		method: 'GET' | 'POST';
		headers?: IDataObject;
		body?: IDataObject;
		formData?: IDataObject;
		timeout?: number;
	},
): Promise<IDataObject> {
	// JSON requests are used by split manifests and /run tool invocations.
	const response = await context.helpers.httpRequest({
		url: options.url,
		method: options.method,
		headers: options.headers,
		body: options.body,
		formData: options.formData,
		json: true,
		timeout: options.timeout ?? 600000,
	});

	if (!response || typeof response !== 'object') {
		throw new NodeOperationError(context.getNode(), 'Toolhub returned an unexpected non-JSON response');
	}

	return response as IDataObject;
}

export async function requestToolhubBuffer(
	context: IExecuteFunctions,
	options: {
		url: string;
		headers?: IDataObject;
		timeout?: number;
	},
): Promise<Buffer> {
	// Binary downloads are required for chunk payload forwarding.
	const response = await context.helpers.httpRequest({
		url: options.url,
		method: 'GET',
		headers: options.headers,
		json: false,
		encoding: null,
		timeout: options.timeout ?? 600000,
	});

	if (Buffer.isBuffer(response)) {
		return response;
	}

	if (response instanceof ArrayBuffer) {
		return Buffer.from(response);
	}

	if (typeof response === 'string') {
		return Buffer.from(response);
	}

	return Buffer.from(JSON.stringify(response ?? {}));
}
