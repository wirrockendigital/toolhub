import type {
	IDataObject,
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
} from 'n8n-workflow';
import {
	buildAuthHeaders,
	buildToolhubUrl,
	getToolhubCredentials,
	requestToolhubJson,
} from '../shared/ToolhubApiClient';

export class ToolhubWol implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'Toolhub WOL',
		name: 'toolhubWol',
		icon: 'fa:power-off',
		group: ['transform'],
		version: 1,
		description: 'Send Wake-on-LAN command through /run alias n8n_wol',
		defaults: {
			name: 'Toolhub WOL',
		},
		inputs: ['main'],
		outputs: ['main'],
		credentials: [{ name: 'toolhubApi', required: true }],
		properties: [
			{ displayName: 'Target', name: 'target', type: 'string', default: '', required: true, description: 'MAC address or configured device alias' },
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const out: INodeExecutionData[] = [];
		const credentials = getToolhubCredentials(this);
		const headers = buildAuthHeaders(credentials);
		const endpointUrl = buildToolhubUrl(credentials.baseUrl, '/run');

		for (let i = 0; i < items.length; i++) {
			// Forward the target to the n8n-specific alias in /run.
			const payload: IDataObject = {
				target: this.getNodeParameter('target', i) as string,
			};

			const response = await requestToolhubJson(this, {
				url: endpointUrl,
				method: 'POST',
				headers,
				body: {
					tool: 'n8n_wol',
					payload,
				},
			});

			out.push({ json: response });
		}

		return [out];
	}
}
