declare module "@modelcontextprotocol/sdk/server" {
  interface ServerConfig {
    name: string;
    version: string;
  }

  interface ServerOptions {
    capabilities?: Record<string, unknown>;
  }

  export class Server {
    constructor(config: ServerConfig, options?: ServerOptions);
    registerTool?(definition: unknown): void;
    tool?(definition: unknown): void;
    start?(transport?: unknown): Promise<void>;
    connect?(transport: unknown): Promise<void>;
  }
}

declare module "@modelcontextprotocol/sdk/transports/stdio" {
  export class StdioServerTransport {}
}
