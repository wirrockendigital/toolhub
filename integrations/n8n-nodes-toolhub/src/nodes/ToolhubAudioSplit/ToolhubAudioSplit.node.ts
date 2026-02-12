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
	requestToolhubBuffer,
	requestToolhubJson,
} from '../shared/ToolhubApiClient';

export class ToolhubAudioSplit implements INodeType {
		description: INodeTypeDescription = {
		displayName: 'Toolhub Audio Split',
		name: 'toolhubAudioSplit',
		icon: 'fa:wave-square',
		group: ['transform'],
		version: 1,
		description: 'Upload audio to Toolhub, split it, and return binary chunk items',
		defaults: {
			name: 'Toolhub Audio Split',
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
				displayName: 'Input Binary Field',
				name: 'binaryPropertyName',
				type: 'string',
				default: 'audio',
				description: 'Binary field that contains the source audio',
			},
			{
				displayName: 'Output Binary Field',
				name: 'outputBinaryPropertyName',
				type: 'string',
				default: 'audioChunk',
				description: 'Binary field name used for each returned chunk',
			},
			{
				displayName: 'Split Mode',
				name: 'splitMode',
				type: 'options',
				options: [
					{
						name: 'Hard (Fixed Seconds)',
						value: 'hard',
					},
					{
						name: 'Silence Before Boundary',
						value: 'silence',
					},
				],
				default: 'hard',
				description: 'How split points are selected',
			},
			{
				displayName: 'Chunk Length Seconds',
				name: 'chunkLengthSeconds',
				type: 'number',
				default: 600,
				typeOptions: {
					minValue: 1,
				},
				description: 'Target chunk length in seconds',
			},
			{
				displayName: 'Enhance Speech',
				name: 'enhanceSpeech',
				type: 'boolean',
				default: true,
				description: 'Enable speech-focused ffmpeg preprocessing before splitting',
			},
			{
				displayName: 'Silence Seek Seconds Before Boundary',
				name: 'silenceSeekSecondsBeforeBoundary',
				type: 'number',
				default: 60,
				typeOptions: {
					minValue: 1,
				},
				description: 'Search window before hard boundary when using silence mode',
				displayOptions: {
					show: {
						splitMode: ['silence'],
					},
				},
			},
			{
				displayName: 'Silence Duration Seconds',
				name: 'silenceDurationSeconds',
				type: 'number',
				default: 0.5,
				typeOptions: {
					minValue: 0.05,
				},
				description: 'Minimum silence duration used by ffmpeg silencedetect',
				displayOptions: {
					show: {
						splitMode: ['silence'],
					},
				},
			},
			{
				displayName: 'Silence Threshold dB',
				name: 'silenceThresholdDb',
				type: 'number',
				default: -30,
				description: 'Silence threshold in decibels',
				displayOptions: {
					show: {
						splitMode: ['silence'],
					},
				},
			},
			{
				displayName: 'Padding Seconds',
				name: 'paddingSeconds',
				type: 'number',
				default: 0,
				typeOptions: {
					minValue: 0,
				},
				description: 'Subtract this value before the selected split point',
				displayOptions: {
					show: {
						splitMode: ['silence'],
					},
				},
			},
			{
				displayName: 'Recording ID',
				name: 'recordingId',
				type: 'string',
				default: '',
				description: 'Optional stable recording identifier',
			},
			{
				displayName: 'Title',
				name: 'title',
				type: 'string',
				default: '',
				description: 'Optional title metadata for downstream storage',
			},
			{
				displayName: 'Source',
				name: 'source',
				type: 'string',
				default: 'ios-webhook',
				description: 'Optional source metadata',
			},
			{
				displayName: 'Language',
				name: 'language',
				type: 'string',
				default: 'de',
				description: 'Optional language metadata',
			},
			{
				displayName: 'Captured At',
				name: 'capturedAt',
				type: 'string',
				default: '',
				description: 'Optional ISO timestamp metadata',
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const outItems: INodeExecutionData[] = [];
		const credentials = getToolhubCredentials(this);
		const headers = buildAuthHeaders(credentials);
		const endpointUrl = buildToolhubUrl(credentials.baseUrl, '/n8n_audio_split');

		for (let itemIndex = 0; itemIndex < items.length; itemIndex++) {
			// Pull node parameters per input item so expression values are supported.
			const binaryPropertyName = this.getNodeParameter('binaryPropertyName', itemIndex) as string;
			const outputBinaryPropertyName = this.getNodeParameter('outputBinaryPropertyName', itemIndex) as string;
			const splitMode = this.getNodeParameter('splitMode', itemIndex) as 'hard' | 'silence';
			const chunkLengthSeconds = this.getNodeParameter('chunkLengthSeconds', itemIndex) as number;
			const enhanceSpeech = this.getNodeParameter('enhanceSpeech', itemIndex) as boolean;

			const recordingId = this.getNodeParameter('recordingId', itemIndex) as string;
			const title = this.getNodeParameter('title', itemIndex) as string;
			const source = this.getNodeParameter('source', itemIndex) as string;
			const language = this.getNodeParameter('language', itemIndex) as string;
			const capturedAt = this.getNodeParameter('capturedAt', itemIndex) as string;

			// Validate and load the source binary from the configured input field.
			const sourceBinary = this.helpers.assertBinaryData(itemIndex, binaryPropertyName);
			const sourceBuffer = await this.helpers.getBinaryDataBuffer(itemIndex, binaryPropertyName);
			const sourceFileName = sourceBinary.fileName || `recording_${itemIndex + 1}.m4a`;
			const sourceMimeType = sourceBinary.mimeType || 'audio/mp4';

			// Build multipart form fields that match the Toolhub n8n_audio_split contract.
			const formData: IDataObject = {
				audio: {
					value: sourceBuffer,
					options: {
						filename: sourceFileName,
						contentType: sourceMimeType,
					},
				},
				mode: splitMode === 'hard' ? 'fixed' : 'silence',
				chunk_length: String(chunkLengthSeconds),
				enhance_speech: enhanceSpeech ? 'true' : 'false',
			};

			// Send optional metadata only when the values are set.
			if (recordingId.trim() !== '') formData.recordingId = recordingId;
			if (title.trim() !== '') formData.title = title;
			if (source.trim() !== '') formData.source = source;
			if (language.trim() !== '') formData.language = language;
			if (capturedAt.trim() !== '') formData.capturedAt = capturedAt;

			if (splitMode === 'silence') {
				// Forward silence tuning parameters only when silence mode is selected.
				formData.silence_seek = String(this.getNodeParameter('silenceSeekSecondsBeforeBoundary', itemIndex) as number);
				formData.silence_duration = String(this.getNodeParameter('silenceDurationSeconds', itemIndex) as number);
				formData.silence_threshold = String(this.getNodeParameter('silenceThresholdDb', itemIndex) as number);
				formData.padding = String(this.getNodeParameter('paddingSeconds', itemIndex) as number);
			}

			const splitManifest = await requestToolhubJson(this, {
				url: endpointUrl,
				method: 'POST',
				headers,
				formData,
				timeout: 600000,
			});

			const chunks = Array.isArray(splitManifest.chunks) ? splitManifest.chunks : [];
			if (chunks.length === 0) {
				throw new NodeOperationError(this.getNode(), 'Toolhub returned no chunks for the provided audio', {
					itemIndex,
				});
			}

			const recordingIdResult = String(splitManifest.recordingId || '');
			const jobId = String(splitManifest.jobId || '');
			const meta = (splitManifest.meta || {}) as IDataObject;

			for (const chunk of chunks) {
				const chunkObject = chunk as IDataObject;
				const chunkFilename = String(chunkObject.filename || 'chunk.m4a');
				const chunkMimeType = String(chunkObject.mimeType || 'audio/mp4');
				const chunkDownloadUrl = String(chunkObject.downloadUrl || '');
				const chunkIndex = Number(chunkObject.index || 0);

				if (chunkDownloadUrl === '') {
					throw new NodeOperationError(this.getNode(), `Chunk download URL missing for ${chunkFilename}`, {
						itemIndex,
					});
				}

				// Download each chunk and expose it as a normal n8n binary field.
				const chunkBuffer = await requestToolhubBuffer(this, {
					url: chunkDownloadUrl,
					headers,
					timeout: 600000,
				});
				const preparedBinary = await this.helpers.prepareBinaryData(
					chunkBuffer,
					chunkFilename,
					chunkMimeType,
				);

				outItems.push({
					json: {
						recordingId: recordingIdResult,
						jobId,
						chunkIndex,
						chunkFilename,
						chunkCount: chunks.length,
						title: meta.title || '',
						source: meta.source || '',
						language: meta.language || '',
						capturedAt: meta.capturedAt || '',
					},
					binary: {
						[outputBinaryPropertyName]: preparedBinary,
					},
				});
			}
		}

		return [outItems];
	}
}
