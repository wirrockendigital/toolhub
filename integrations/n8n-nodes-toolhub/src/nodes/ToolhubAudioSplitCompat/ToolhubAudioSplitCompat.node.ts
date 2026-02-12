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

export class ToolhubAudioSplitCompat implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'Toolhub Audio Split Compat',
		name: 'toolhubAudioSplitCompat',
		icon: 'fa:cut',
		group: ['transform'],
		version: 1,
		description: 'Call legacy /audio-split using shared-storage filename contract',
		defaults: {
			name: 'Toolhub Audio Split Compat',
		},
		inputs: ['main'],
		outputs: ['main'],
		credentials: [
			{
				name: 'toolhubApi',
				required: true,
			},
		],
		properties: [
			{
				displayName: 'Filename',
				name: 'filename',
				type: 'string',
				default: '',
				required: true,
				description: 'Filename already present in /shared/audio/in',
			},
			{
				displayName: 'Mode',
				name: 'mode',
				type: 'options',
				options: [
					{ name: 'Fixed', value: 'fixed' },
					{ name: 'Silence', value: 'silence' },
				],
				default: 'fixed',
			},
			{
				displayName: 'Chunk Length Seconds',
				name: 'chunkLengthSeconds',
				type: 'number',
				default: 600,
				typeOptions: { minValue: 1 },
			},
			{
				displayName: 'Enhance Speech',
				name: 'enhanceSpeech',
				type: 'boolean',
				default: true,
			},
			{
				displayName: 'Silence Seek Seconds',
				name: 'silenceSeekSeconds',
				type: 'number',
				default: 60,
				displayOptions: { show: { mode: ['silence'] } },
			},
			{
				displayName: 'Silence Duration Seconds',
				name: 'silenceDurationSeconds',
				type: 'number',
				default: 0.5,
				displayOptions: { show: { mode: ['silence'] } },
			},
			{
				displayName: 'Silence Threshold dB',
				name: 'silenceThresholdDb',
				type: 'number',
				default: -30,
				displayOptions: { show: { mode: ['silence'] } },
			},
			{
				displayName: 'Padding Seconds',
				name: 'paddingSeconds',
				type: 'number',
				default: 0,
				displayOptions: { show: { mode: ['silence'] } },
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const out: INodeExecutionData[] = [];
		const credentials = getToolhubCredentials(this);
		const headers = buildAuthHeaders(credentials);
		const endpointUrl = buildToolhubUrl(credentials.baseUrl, '/audio-split');

		for (let i = 0; i < items.length; i++) {
			// Build a strict JSON payload for the compatibility endpoint.
			const mode = this.getNodeParameter('mode', i) as 'fixed' | 'silence';
			const payload: IDataObject = {
				filename: this.getNodeParameter('filename', i) as string,
				mode,
				chunk_length: this.getNodeParameter('chunkLengthSeconds', i) as number,
				enhance_speech: this.getNodeParameter('enhanceSpeech', i) as boolean,
			};

			if (mode === 'silence') {
				payload.silence_seek = this.getNodeParameter('silenceSeekSeconds', i) as number;
				payload.silence_duration = this.getNodeParameter('silenceDurationSeconds', i) as number;
				payload.silence_threshold = this.getNodeParameter('silenceThresholdDb', i) as number;
				payload.padding = this.getNodeParameter('paddingSeconds', i) as number;
			}

			const response = await requestToolhubJson(this, {
				url: endpointUrl,
				method: 'POST',
				headers,
				body: payload,
			});

			out.push({ json: response });
		}

		return [out];
	}
}
