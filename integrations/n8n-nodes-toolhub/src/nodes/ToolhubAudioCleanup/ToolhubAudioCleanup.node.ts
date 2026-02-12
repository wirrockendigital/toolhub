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

export class ToolhubAudioCleanup implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'Toolhub Audio Cleanup',
		name: 'toolhubAudioCleanup',
		icon: 'fa:broom',
		group: ['transform'],
		version: 1,
		description: 'Run Toolhub cleanup through /run alias n8n_audio_cleanup',
		defaults: {
			name: 'Toolhub Audio Cleanup',
		},
		inputs: ['main'],
		outputs: ['main'],
		credentials: [{ name: 'toolhubApi', required: true }],
		properties: [
			{ displayName: 'Dry Run', name: 'dryRun', type: 'boolean', default: true, description: 'Run cleanup in preview mode without deleting files' },
			{ displayName: 'Logs Directory', name: 'logsDir', type: 'string', default: '' },
			{ displayName: 'Temp Directory', name: 'tmpDir', type: 'string', default: '' },
			{ displayName: 'Temp Max Age Hours', name: 'tmpMaxAgeHours', type: 'number', default: 24, typeOptions: { minValue: 1 } },
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const out: INodeExecutionData[] = [];
		const credentials = getToolhubCredentials(this);
		const headers = buildAuthHeaders(credentials);
		const endpointUrl = buildToolhubUrl(credentials.baseUrl, '/run');

		for (let i = 0; i < items.length; i++) {
			// Build cleanup payload and keep optional arguments out when empty.
			const payload: IDataObject = {
				dry_run: this.getNodeParameter('dryRun', i) as boolean,
				tmp_max_age_hours: this.getNodeParameter('tmpMaxAgeHours', i) as number,
			};

			const logsDir = this.getNodeParameter('logsDir', i) as string;
			const tmpDir = this.getNodeParameter('tmpDir', i) as string;
			if (logsDir.trim() !== '') payload.logs_dir = logsDir;
			if (tmpDir.trim() !== '') payload.tmp_dir = tmpDir;

			const response = await requestToolhubJson(this, {
				url: endpointUrl,
				method: 'POST',
				headers,
				body: {
					tool: 'n8n_audio_cleanup',
					payload,
				},
			});

			out.push({ json: response });
		}

		return [out];
	}
}
