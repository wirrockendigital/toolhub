import type {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
} from 'n8n-workflow';
import { executeJsonToolNode } from '../shared/ToolhubRunHelpers';

export class ToolhubDownloadAria2 implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'Toolhub Download Aria2',
		name: 'toolhubDownloadAria2',
		icon: 'fa:terminal',
		group: ['transform'],
		version: 1,
		description: 'Download files using aria2 via Toolhub /run',
		defaults: {
			name: 'Toolhub Download Aria2',
		},
		inputs: ['main'],
		outputs: ['main'],
		credentials: [{ name: 'toolhubApi', required: true }],
		properties: [
			{
				displayName: 'Payload JSON',
				name: 'payloadJson',
				type: 'json',
				default: '{}',
				description: 'Payload values forwarded to Toolhub /run for this tool.',
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		// Delegate node execution to the shared JSON-tool runner.
		return executeJsonToolNode(this, { toolAlias: 'n8n_download_aria2' });
	}
}
