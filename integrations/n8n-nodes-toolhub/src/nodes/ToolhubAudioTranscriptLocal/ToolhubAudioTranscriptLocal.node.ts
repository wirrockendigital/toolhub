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

export class ToolhubAudioTranscriptLocal implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'Toolhub Audio Transcript Local',
		name: 'toolhubAudioTranscriptLocal',
		icon: 'fa:file-audio',
		group: ['transform'],
		version: 1,
		description: 'Run local Toolhub transcript backend through /run alias n8n_audio_transcript_local',
		defaults: {
			name: 'Toolhub Audio Transcript Local',
		},
		inputs: ['main'],
		outputs: ['main'],
		credentials: [{ name: 'toolhubApi', required: true }],
		properties: [
			{ displayName: 'Input', name: 'input', type: 'string', default: '', required: true, description: 'Audio input path or filename' },
			{ displayName: 'Output', name: 'output', type: 'string', default: '' },
			{ displayName: 'Format', name: 'format', type: 'options', options: [{ name: 'JSON', value: 'json' }, { name: 'Text', value: 'txt' }, { name: 'SRT', value: 'srt' }], default: 'json' },
			{ displayName: 'Backend', name: 'backend', type: 'options', options: [{ name: 'Auto', value: 'auto' }, { name: 'Whisper CLI', value: 'whisper-cli' }], default: 'auto' },
			{ displayName: 'Language', name: 'language', type: 'string', default: 'de' },
			{ displayName: 'Model', name: 'model', type: 'string', default: '' },
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const out: INodeExecutionData[] = [];
		const credentials = getToolhubCredentials(this);
		const headers = buildAuthHeaders(credentials);
		const endpointUrl = buildToolhubUrl(credentials.baseUrl, '/run');

		for (let i = 0; i < items.length; i++) {
			// Build /run payload with the required n8n_audio_* alias name.
			const payload: IDataObject = {
				input: this.getNodeParameter('input', i) as string,
				format: this.getNodeParameter('format', i) as string,
				backend: this.getNodeParameter('backend', i) as string,
				language: this.getNodeParameter('language', i) as string,
			};

			const outputPath = this.getNodeParameter('output', i) as string;
			const modelName = this.getNodeParameter('model', i) as string;
			if (outputPath.trim() !== '') payload.output = outputPath;
			if (modelName.trim() !== '') payload.model = modelName;

			const response = await requestToolhubJson(this, {
				url: endpointUrl,
				method: 'POST',
				headers,
				body: {
					tool: 'n8n_audio_transcript_local',
					payload,
				},
			});

			out.push({ json: response });
		}

		return [out];
	}
}
