import type {
	IDataObject,
	IExecuteFunctions,
	INodeExecutionData,
} from 'n8n-workflow';
import { NodeOperationError } from 'n8n-workflow';
import {
	buildAuthHeaders,
	buildToolhubUrl,
	getToolhubCredentials,
	requestToolhubArtifact,
	requestToolhubJson,
	requestToolhubMultipart,
} from './ToolhubApiClient';

export interface JsonToolExecutionConfig {
	toolAlias: string;
}

export interface FileToolExecutionConfig {
	toolAlias: string;
}

export async function executeJsonToolNode(
	context: IExecuteFunctions,
	config: JsonToolExecutionConfig,
): Promise<INodeExecutionData[][]> {
	const items = context.getInputData();
	const out: INodeExecutionData[] = [];
	const credentials = getToolhubCredentials(context);
	const headers = buildAuthHeaders(credentials);
	const endpointUrl = buildToolhubUrl(credentials.baseUrl, '/run');

	for (let i = 0; i < items.length; i++) {
		// Parse payload per item so expressions can drive request content.
		const payload = context.getNodeParameter('payloadJson', i) as IDataObject;
		const response = await requestToolhubJson(context, {
			url: endpointUrl,
			method: 'POST',
			headers,
			body: {
				tool: config.toolAlias,
				payload,
			},
		});
		out.push({ json: response });
	}

	return [out];
}

export async function executeFileToolNode(
	context: IExecuteFunctions,
	config: FileToolExecutionConfig,
): Promise<INodeExecutionData[][]> {
	const items = context.getInputData();
	const out: INodeExecutionData[] = [];
	const credentials = getToolhubCredentials(context);
	const headers = buildAuthHeaders(credentials);
	const endpointUrl = buildToolhubUrl(credentials.baseUrl, '/run-file');

	for (let i = 0; i < items.length; i++) {
		// Resolve binary input and optional payload for file-first processing.
		const inputField = context.getNodeParameter('inputBinaryPropertyName', i) as string;
		const outputField = context.getNodeParameter('outputBinaryPropertyName', i) as string;
		const payload = context.getNodeParameter('payloadJson', i) as IDataObject;
		const downloadFirstArtifact = context.getNodeParameter('downloadFirstArtifact', i) as boolean;

		const sourceBinary = context.helpers.assertBinaryData(i, inputField);
		const sourceBuffer = await context.helpers.getBinaryDataBuffer(i, inputField);
		const sourceFileName = sourceBinary.fileName || `toolhub_input_${i + 1}.bin`;
		const sourceMimeType = sourceBinary.mimeType || 'application/octet-stream';

		const formData: IDataObject = {
			tool: config.toolAlias,
			payload: JSON.stringify(payload ?? {}),
			file: {
				value: sourceBuffer,
				options: {
					filename: sourceFileName,
					contentType: sourceMimeType,
				},
			},
		};

		const response = await requestToolhubMultipart(context, {
			url: endpointUrl,
			headers,
			formData,
		});

		const resultItem: INodeExecutionData = { json: response };
		const artifacts = Array.isArray(response.artifacts) ? response.artifacts : [];
		if (downloadFirstArtifact && artifacts.length > 0) {
			const firstArtifact = artifacts[0] as IDataObject;
			const downloadUrl = String(firstArtifact.downloadUrl || '');
			if (downloadUrl === '') {
				throw new NodeOperationError(context.getNode(), 'Toolhub run-file response is missing artifact downloadUrl', {
					itemIndex: i,
				});
			}

			// Download first artifact to expose immediate binary output in n8n.
			const artifactBuffer = await requestToolhubArtifact(context, {
				url: downloadUrl,
				headers,
			});
			const artifactName = String(firstArtifact.filename || `artifact_${i + 1}.bin`);
			const artifactMime = String(firstArtifact.mimeType || 'application/octet-stream');
			const preparedBinary = await context.helpers.prepareBinaryData(artifactBuffer, artifactName, artifactMime);
			resultItem.binary = {
				[outputField]: preparedBinary,
			};
		}

		out.push(resultItem);
	}

	return [out];
}
