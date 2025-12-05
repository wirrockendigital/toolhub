import { z } from "zod";
import { coerceBoolean, csvToList } from "./schemas.js";

const envSchema = z.object({
  SAFE_MODE: z.string().optional(),
  ALLOWLIST_PATHS: z.string().optional(),
  ALLOWLIST_HOSTS: z.string().optional(),
  MCP_COMMAND_TIMEOUT_MS: z.string().optional(),
  MCP_RATE_LIMIT_COUNT: z.string().optional(),
  MCP_RATE_LIMIT_WINDOW_MS: z.string().optional(),
  MCP_MAX_OUTPUT: z.string().optional(),
  MCP_SCRIPTS_ROOT: z.string().optional(),
  MCP_SERVER_NAME: z.string().optional(),
  MCP_SERVER_VERSION: z.string().optional(),
  NUCLEI_TEMPLATES: z.string().optional(),
});

export interface McpConfig {
  safeMode: boolean;
  allowlistPaths: string[];
  allowlistHosts: string[];
  commandTimeoutMs: number;
  maxOutputLength: number;
  rateLimitCount: number;
  rateLimitWindowMs: number;
  scriptsRoot: string;
  serverName: string;
  serverVersion: string;
  nucleiTemplatesDir?: string;
}

const DEFAULTS = {
  SAFE_MODE: true,
  ALLOWLIST_PATHS: ["/data", "/tmp"],
  ALLOWLIST_HOSTS: ["localhost", "127.0.0.1"],
  COMMAND_TIMEOUT_MS: 120_000,
  MAX_OUTPUT: 20_000,
  RATE_LIMIT_COUNT: 5,
  RATE_LIMIT_WINDOW_MS: 10_000,
  SCRIPTS_ROOT: "/app/scripts",
  SERVER_NAME: "toolhub-mcp",
  SERVER_VERSION: "0.1.1",
};

export function loadConfig(env: NodeJS.ProcessEnv = process.env): McpConfig {
  const parsed = envSchema.parse(env);

  return {
    safeMode: coerceBoolean(parsed.SAFE_MODE, DEFAULTS.SAFE_MODE),
    allowlistPaths: csvToList(parsed.ALLOWLIST_PATHS, DEFAULTS.ALLOWLIST_PATHS),
    allowlistHosts: csvToList(parsed.ALLOWLIST_HOSTS, DEFAULTS.ALLOWLIST_HOSTS),
    commandTimeoutMs: parsed.MCP_COMMAND_TIMEOUT_MS
      ? Number.parseInt(parsed.MCP_COMMAND_TIMEOUT_MS, 10)
      : DEFAULTS.COMMAND_TIMEOUT_MS,
    maxOutputLength: parsed.MCP_MAX_OUTPUT
      ? Number.parseInt(parsed.MCP_MAX_OUTPUT, 10)
      : DEFAULTS.MAX_OUTPUT,
    rateLimitCount: parsed.MCP_RATE_LIMIT_COUNT
      ? Number.parseInt(parsed.MCP_RATE_LIMIT_COUNT, 10)
      : DEFAULTS.RATE_LIMIT_COUNT,
    rateLimitWindowMs: parsed.MCP_RATE_LIMIT_WINDOW_MS
      ? Number.parseInt(parsed.MCP_RATE_LIMIT_WINDOW_MS, 10)
      : DEFAULTS.RATE_LIMIT_WINDOW_MS,
    scriptsRoot: parsed.MCP_SCRIPTS_ROOT ?? DEFAULTS.SCRIPTS_ROOT,
    serverName: parsed.MCP_SERVER_NAME ?? DEFAULTS.SERVER_NAME,
    serverVersion: parsed.MCP_SERVER_VERSION ?? DEFAULTS.SERVER_VERSION,
    nucleiTemplatesDir: parsed.NUCLEI_TEMPLATES,
  };
}
