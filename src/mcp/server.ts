#!/usr/bin/env node
import process from "node:process";
import { Server } from "@modelcontextprotocol/sdk/server";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadConfig } from "./config.js";
import { createToolRegistry } from "./tool-registry.js";

interface ToolResponseContent {
  type: string;
  text: string;
}

async function main(): Promise<void> {
  const config = loadConfig();
  const tools = await createToolRegistry(config);

  if (process.argv.includes("--list-tools")) {
    const summary = tools.map((tool) => ({
      name: tool.name,
      description: tool.description,
      schema: tool.schema.json,
    }));
    process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
    return;
  }

  const server = new Server(
    {
      name: config.serverName,
      version: config.serverVersion,
    },
    {
      capabilities: {
        tools: {},
      },
    },
  );

  for (const tool of tools) {
    const definition = {
      name: tool.name,
      description: tool.description,
      inputSchema: tool.schema.json,
      handler: async (input: unknown) => {
        try {
          const result = await tool.handler(input);
          const content: ToolResponseContent[] = [
            {
              type: "text",
              text: result.output,
            },
          ];
          return {
            content,
            isError: result.exitCode !== 0,
            metadata: result.truncated ? { truncated: true } : undefined,
          };
        } catch (error) {
          return {
            isError: true,
            content: [
              {
                type: "text",
                text: formatError(error),
              },
            ],
          };
        }
      },
    };

    if (typeof (server as any).registerTool === "function") {
      (server as any).registerTool(definition);
    } else if (typeof (server as any).tool === "function") {
      (server as any).tool(definition);
    } else {
      throw new Error("MCP SDK version does not expose registerTool/tool helpers");
    }
  }

  const transport = new StdioServerTransport();
  if (typeof (server as any).start === "function" && (server as any).start.length > 0) {
    await (server as any).start(transport);
  } else {
    await (server as any).connect(transport);
    await (server as any).start();
  }
}

function formatError(error: unknown): string {
  if (error instanceof Error) {
    return `${error.name}: ${error.message}`;
  }
  return `Unexpected error: ${String(error)}`;
}

main().catch((error) => {
  process.stderr.write(`${formatError(error)}\n`);
  process.exit(1);
});
