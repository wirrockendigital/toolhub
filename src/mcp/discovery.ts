import fs from "node:fs/promises";
import path from "node:path";
import fg from "fast-glob";
import { DefaultArgsSchema, JsonSchema, ToolInputSchema, jsonSchemaToZod } from "./schemas.js";

const METADATA_START = "#==MCP==";
const METADATA_END = "#==/MCP==";

export interface ScriptToolDefinition {
  name: string;
  description: string;
  command: string;
  args: string[];
  scriptPath: string;
  schema: ToolInputSchema;
}

interface MetadataBlock {
  description?: string;
  schema?: JsonSchema;
}

export async function discoverScripts(root: string): Promise<ScriptToolDefinition[]> {
  const pattern = path.join(root, "**/*.{sh,py}").replace(/\\/g, "/");
  const entries = await fg(pattern, { dot: false, onlyFiles: true, followSymbolicLinks: false, unique: true });

  const tools: ScriptToolDefinition[] = [];

  for (const scriptPath of entries.sort()) {
    const stat = await fs.stat(scriptPath).catch(() => undefined);
    if (!stat) {
      continue;
    }

    const isExecutable = (stat.mode & 0o111) !== 0;
    if (!isExecutable) {
      continue;
    }

    const contents = await fs.readFile(scriptPath, "utf8");
    const metadata = parseMetadata(contents);
    const { name, description } = buildNameAndDescription(scriptPath, metadata?.description);
    const schema = metadata?.schema ? buildSchema(metadata.schema) : DefaultArgsSchema;

    const command = scriptPath.endsWith(".py") ? "python3" : "bash";
    const args = scriptPath.endsWith(".py") ? [scriptPath] : [scriptPath];

    tools.push({
      name,
      description,
      command,
      args,
      scriptPath,
      schema,
    });
  }

  return tools;
}

function buildNameAndDescription(scriptPath: string, metadataDescription?: string): {
  name: string;
  description: string;
} {
  const basename = path.basename(scriptPath);
  const [rawName, extension] = basename.split(/\.(?=[^.]+$)/);
  const prefix = extension === "py" ? "py" : "sh";
  const normalised = rawName.toLowerCase().replace(/[^a-z0-9]+/g, "_");
  const name = `${prefix}_${normalised}`;
  const description = metadataDescription ?? `Execute Toolhub script ${basename}`;
  return { name, description };
}

function parseMetadata(contents: string): MetadataBlock | undefined {
  const startIndex = contents.indexOf(METADATA_START);
  const endIndex = contents.indexOf(METADATA_END);
  if (startIndex === -1 || endIndex === -1 || endIndex <= startIndex) {
    return undefined;
  }

  const rawBlock = contents.slice(startIndex + METADATA_START.length, endIndex);
  const cleaned = rawBlock
    .split(/\r?\n/)
    .map((line) => line.replace(/^\s*#\s?/, "").trim())
    .filter((line) => line.length > 0)
    .join("");

  try {
    const parsed = JSON.parse(cleaned) as MetadataBlock;
    return parsed;
  } catch (error) {
    return undefined;
  }
}

function buildSchema(schema: JsonSchema): ToolInputSchema {
  try {
    const zod = jsonSchemaToZod(schema);
    return { zod, json: schema };
  } catch (error) {
    return DefaultArgsSchema;
  }
}
