import type { ICredentialType, INodeProperties } from 'n8n-workflow';

export class ToolhubApi implements ICredentialType {
	// This name is referenced by all Toolhub nodes.
	name = 'toolhubApi';

	// This display name is shown in the n8n credentials UI.
	displayName = 'Toolhub API';

	// This documentation URL explains local/self-hosted usage.
	documentationUrl = 'https://github.com/toolhub/toolhub';

	properties: INodeProperties[] = [
		{
			displayName: 'Base URL',
			name: 'baseUrl',
			type: 'string',
			default: 'http://toolhub:5656',
			required: true,
			description: 'Base URL of your Toolhub webhook service',
		},
		{
			displayName: 'API Key',
			name: 'apiKey',
			type: 'string',
			typeOptions: {
				password: true,
			},
			default: '',
			description: 'Optional API key for Toolhub authentication',
		},
		{
			displayName: 'Auth Header Name',
			name: 'authHeaderName',
			type: 'string',
			default: 'Authorization',
			description: 'Header used when API Key is configured',
		},
		{
			displayName: 'Auth Scheme',
			name: 'authScheme',
			type: 'options',
			options: [
				{
					name: 'Bearer',
					value: 'bearer',
				},
				{
					name: 'Token',
					value: 'token',
				},
				{
					name: 'Raw',
					value: 'raw',
				},
			],
			default: 'bearer',
			description: 'Prefix format for the optional API key header value',
		},
	];
}
