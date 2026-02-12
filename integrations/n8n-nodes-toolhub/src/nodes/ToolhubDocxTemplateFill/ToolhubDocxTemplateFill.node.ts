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

export class ToolhubDocxTemplateFill implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'Toolhub DOCX Template Fill',
		name: 'toolhubDocxTemplateFill',
		icon: 'fa:file-signature',
		group: ['transform'],
		version: 1,
		description: 'Fill DOCX template through /run alias n8n_docx_template_fill',
		defaults: {
			name: 'Toolhub DOCX Template Fill',
		},
		inputs: ['main'],
		outputs: ['main'],
		credentials: [{ name: 'toolhubApi', required: true }],
		properties: [
			{ displayName: 'Template', name: 'template', type: 'string', default: '', required: true },
			{ displayName: 'Output Filename', name: 'outputFilename', type: 'string', default: '' },
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
			// Parse template data as JSON to avoid string-only payload bugs.
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

			const outputFilename = this.getNodeParameter('outputFilename', i) as string;
			if (outputFilename.trim() !== '') payload.output_filename = outputFilename;

			const response = await requestToolhubJson(this, {
				url: endpointUrl,
				method: 'POST',
				headers,
				body: {
					tool: 'n8n_docx_template_fill',
					payload,
				},
			});

			out.push({ json: response });
		}

		return [out];
	}
}
