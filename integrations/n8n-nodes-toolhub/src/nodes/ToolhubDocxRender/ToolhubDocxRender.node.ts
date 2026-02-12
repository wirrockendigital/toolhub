import type {
	IDataObject,
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
} from 'n8n-workflow';
import { NodeOperationError } from 'n8n-workflow';
import {
	buildAuthHeaders,
	buildToolhubUrl,
	getToolhubCredentials,
	requestToolhubJson,
} from '../shared/ToolhubApiClient';

export class ToolhubDocxRender implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'Toolhub DOCX Render',
		name: 'toolhubDocxRender',
		icon: 'fa:file-word',
		group: ['transform'],
		version: 1,
		description: 'Render DOCX template through /run alias n8n_docx_render',
		defaults: {
			name: 'Toolhub DOCX Render',
		},
		inputs: ['main'],
		outputs: ['main'],
		credentials: [{ name: 'toolhubApi', required: true }],
		properties: [
			{ displayName: 'Template', name: 'template', type: 'string', default: '', required: true },
			{ displayName: 'Output Name', name: 'outputName', type: 'string', default: '' },
			{ displayName: 'Data JSON', name: 'dataJson', type: 'json', default: '{}' },
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const out: INodeExecutionData[] = [];
		const credentials = getToolhubCredentials(this);
		const headers = buildAuthHeaders(credentials);
		const endpointUrl = buildToolhubUrl(credentials.baseUrl, '/run');

		for (let i = 0; i < items.length; i++) {
			// Parse the data JSON to ensure templates receive structured values.
			let parsedData: IDataObject;
			try {
				parsedData = this.getNodeParameter('dataJson', i) as IDataObject;
			} catch (error) {
				throw new NodeOperationError(this.getNode(), `Invalid Data JSON: ${(error as Error).message}`, {
					itemIndex: i,
				});
			}

			const payload: IDataObject = {
				template: this.getNodeParameter('template', i) as string,
				data: parsedData,
			};

			const outputName = this.getNodeParameter('outputName', i) as string;
			if (outputName.trim() !== '') payload.output_name = outputName;

			const response = await requestToolhubJson(this, {
				url: endpointUrl,
				method: 'POST',
				headers,
				body: {
					tool: 'n8n_docx_render',
					payload,
				},
			});

			out.push({ json: response });
		}

		return [out];
	}
}
