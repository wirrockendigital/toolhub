import type {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
} from 'n8n-workflow';
import { executeFileToolNode } from '../shared/ToolhubRunHelpers';

export class ToolhubPdfInfoRead implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'Toolhub PDF Info',
		name: 'toolhubPdfInfoRead',
		icon: 'fa:file',
		group: ['transform'],
		version: 1,
		description: 'Read PDF metadata through Toolhub run-file',
		defaults: {
			name: 'Toolhub PDF Info',
		},
		inputs: ['main'],
		outputs: ['main'],
		credentials: [{ name: 'toolhubApi', required: true }],
		properties: [
			{
				displayName: 'Input Binary Field',
				name: 'inputBinaryPropertyName',
				type: 'string',
				default: 'data',
				description: 'Binary field containing the input file.',
			},
			{
				displayName: 'Output Binary Field',
				name: 'outputBinaryPropertyName',
				type: 'string',
				default: 'artifact',
				description: 'Binary field used for the first downloaded artifact.',
			},
			{
				displayName: 'Payload JSON',
				name: 'payloadJson',
				type: 'json',
				default: '{}',
				description: 'Additional payload values forwarded to Toolhub run-file.',
			},
			{
				displayName: 'Download First Artifact',
				name: 'downloadFirstArtifact',
				type: 'boolean',
				default: true,
				description: 'Download the first artifact and expose it as n8n binary output.',
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		// Delegate node execution to the shared file-tool runner.
		return executeFileToolNode(this, { toolAlias: 'n8n_pdf_info_read' });
	}
}
