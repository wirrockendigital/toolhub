import type {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
} from 'n8n-workflow';
import { executeJsonToolNode } from '../shared/ToolhubRunHelpers';

export class ToolhubCalcBc implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'Toolhub BC Calc',
		name: 'toolhubCalcBc',
		icon: 'fa:terminal',
		group: ['transform'],
		version: 1,
		description: 'Evaluate expressions via bc through Toolhub /run',
		defaults: {
			name: 'Toolhub BC Calc',
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
		return executeJsonToolNode(this, { toolAlias: 'n8n_calc_bc' });
	}
}
