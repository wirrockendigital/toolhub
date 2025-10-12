import { promises as fs, constants as fsConstants } from "node:fs";
import path from "node:path";
import { z } from "zod";
import { McpConfig } from "./config.js";
import { discoverScripts, ScriptToolDefinition } from "./discovery.js";
import { RateLimiter, SecurityError, ensureHostAllowed, ensurePathAllowed } from "./security.js";
import { DefaultArgsSchema, ToolInputSchema, normaliseArgs } from "./schemas.js";
import { runCommand } from "./util/run.js";

export interface ToolExecutionResult {
  output: string;
  truncated: boolean;
  exitCode: number;
}

export interface RegisteredTool {
  name: string;
  description: string;
  schema: ToolInputSchema;
  handler: (input: unknown) => Promise<ToolExecutionResult>;
}

const CLI_WHITELIST: Array<{
  name: string;
  commands: string[];
  description: string;
}> = [
  { name: "ffmpeg", commands: ["ffmpeg"], description: "Execute the ffmpeg multimedia CLI." },
  { name: "sox", commands: ["sox"], description: "Execute the SoX audio processing CLI." },
  { name: "magick", commands: ["magick", "convert"], description: "Execute ImageMagick (magick/convert)." },
  { name: "tesseract", commands: ["tesseract"], description: "Execute the Tesseract OCR engine." },
  { name: "pdftotext", commands: ["pdftotext"], description: "Execute pdftotext from poppler-utils." },
  { name: "pdfinfo", commands: ["pdfinfo"], description: "Execute pdfinfo from poppler-utils." },
  { name: "jq", commands: ["jq"], description: "Execute the jq JSON processor." },
  { name: "curl", commands: ["curl"], description: "Execute curl for HTTP requests (restricted by allowlist)." },
  { name: "exiftool", commands: ["exiftool"], description: "Execute ExifTool metadata inspector." },
  { name: "syft", commands: ["syft"], description: "Execute Anchore Syft software bill-of-materials scanner." },
  { name: "grype", commands: ["grype"], description: "Execute Anchore Grype vulnerability scanner." },
  { name: "trivy", commands: ["trivy"], description: "Execute Trivy vulnerability scanner." },
  { name: "nuclei", commands: ["nuclei"], description: "Execute ProjectDiscovery nuclei (safe-mode restrictions apply)." },
];

export async function createToolRegistry(config: McpConfig): Promise<RegisteredTool[]> {
  const rateLimiter = new RateLimiter(config.rateLimitCount, config.rateLimitWindowMs);
  const scripts = await discoverScripts(config.scriptsRoot);
  const scriptMap = new Map(scripts.map((tool) => [tool.name, tool]));

  const discoveredTools = scripts.map((tool) => createScriptTool(tool, config, rateLimiter));
  const cliTools = await createCliTools(config, rateLimiter);
  const handcrafted = await createHandcraftedTools(config, rateLimiter, scriptMap);

  return [...discoveredTools, ...cliTools, ...handcrafted];
}

function createScriptTool(tool: ScriptToolDefinition, config: McpConfig, limiter: RateLimiter): RegisteredTool {
  return {
    name: tool.name,
    description: tool.description,
    schema: tool.schema,
    handler: async (input: unknown) => {
      limiter.check(tool.name);
      const parsed = tool.schema.zod.parse(input ?? {});
      const args = normaliseArgs((parsed as { args?: string[] }).args);
      const generatedArgs = buildCliArgsFromObject(parsed, new Set(["args"]));
      const result = await runCommand(
        tool.name,
        tool.command,
        [...tool.args, ...generatedArgs, ...args],
        config,
      );
      return { ...result };
    },
  };
}

async function createCliTools(config: McpConfig, limiter: RateLimiter): Promise<RegisteredTool[]> {
  const tools: RegisteredTool[] = [];
  for (const entry of CLI_WHITELIST) {
    const executable = await resolveExecutable(entry.commands);
    if (!executable) {
      continue;
    }

    tools.push({
      name: entry.name,
      description: entry.description,
      schema: DefaultArgsSchema,
      handler: async (input: unknown) => {
        limiter.check(entry.name);
        const parsed = DefaultArgsSchema.zod.parse(input ?? {});
        const args = normaliseArgs(parsed.args);
        for (const candidate of args) {
          if (candidate.startsWith("/")) {
            ensurePathAllowed(candidate, config);
          }
          if (candidate.includes("://")) {
            ensureHostAllowed(candidate, config);
          }
        }
        const result = await runCommand(entry.name, executable, args, config);
        return { ...result };
      },
    });
  }
  return tools;
}

async function createHandcraftedTools(
  config: McpConfig,
  limiter: RateLimiter,
  scriptMap: Map<string, ScriptToolDefinition>,
): Promise<RegisteredTool[]> {
  const tools: RegisteredTool[] = [];

  if (await hasExecutable("pdftotext")) {
    const schema: ToolInputSchema = {
      zod: z.object({
        path: z.string(),
      }),
      json: {
        type: "object",
        properties: {
          path: { type: "string", description: "Absolute or relative path to the PDF file." },
        },
        required: ["path"],
      },
    };

    tools.push({
      name: "pdftotext_extract",
      description: "Extract raw text from a PDF file using pdftotext.",
      schema,
      handler: async (input: unknown) => {
        limiter.check("pdftotext_extract");
        const parsed = schema.zod.parse(input ?? {});
        ensurePathAllowed(parsed.path, config);
        const result = await runCommand("pdftotext_extract", "pdftotext", [parsed.path, "-"], config);
        return { ...result };
      },
    });
  }

  if (await hasExecutable("pdfinfo")) {
    const schema: ToolInputSchema = {
      zod: z.object({ path: z.string() }),
      json: {
        type: "object",
        properties: {
          path: { type: "string", description: "Absolute or relative path to the PDF file." },
        },
        required: ["path"],
      },
    };

    tools.push({
      name: "pdfinfo_read",
      description: "Read PDF metadata using pdfinfo.",
      schema,
      handler: async (input: unknown) => {
        limiter.check("pdfinfo_read");
        const parsed = schema.zod.parse(input ?? {});
        ensurePathAllowed(parsed.path, config);
        const result = await runCommand("pdfinfo_read", "pdfinfo", [parsed.path], config);
        return { ...result };
      },
    });
  }

  if (await hasExecutable("ffprobe")) {
    const schema: ToolInputSchema = {
      zod: z.object({ path: z.string() }),
      json: {
        type: "object",
        properties: {
          path: { type: "string", description: "Absolute or relative path to the media file." },
        },
        required: ["path"],
      },
    };

    tools.push({
      name: "ffprobe_info",
      description: "Inspect media streams using ffprobe (JSON output).",
      schema,
      handler: async (input: unknown) => {
        limiter.check("ffprobe_info");
        const parsed = schema.zod.parse(input ?? {});
        ensurePathAllowed(parsed.path, config);
        const args = ["-v", "error", "-show_format", "-show_streams", "-of", "json", parsed.path];
        const result = await runCommand("ffprobe_info", "ffprobe", args, config);
        return { ...result };
      },
    });
  }

  if (await hasExecutable("tesseract")) {
    const schema: ToolInputSchema = {
      zod: z.object({
        imagePath: z.string(),
        lang: z.string().optional(),
      }),
      json: {
        type: "object",
        properties: {
          imagePath: { type: "string", description: "Path to the image to OCR." },
          lang: { type: "string", description: "Optional Tesseract language code (e.g., eng)." },
        },
        required: ["imagePath"],
      },
    };

    tools.push({
      name: "tesseract_ocr",
      description: "Perform OCR on an image using Tesseract (stdout output).",
      schema,
      handler: async (input: unknown) => {
        limiter.check("tesseract_ocr");
        const parsed = schema.zod.parse(input ?? {});
        ensurePathAllowed(parsed.imagePath, config);
        const args = [parsed.imagePath, "stdout"];
        if (parsed.lang) {
          args.push("-l", parsed.lang);
        }
        const result = await runCommand("tesseract_ocr", "tesseract", args, config);
        return { ...result };
      },
    });
  }

  if (await hasExecutable("nuclei")) {
    const schema: ToolInputSchema = {
      zod: z.object({
        url: z.string(),
        tags: z.array(z.string()).optional(),
      }),
      json: {
        type: "object",
        properties: {
          url: { type: "string", description: "Target URL or hostname." },
          tags: {
            type: "array",
            items: { type: "string" },
            description: "Optional nuclei template tags (info,misconfiguration).",
          },
        },
        required: ["url"],
      },
    };

    tools.push({
      name: "nuclei_safe",
      description: "Run nuclei with safe-mode defaults (info/low severity).",
      schema,
      handler: async (input: unknown) => {
        limiter.check("nuclei_safe");
        const parsed = schema.zod.parse(input ?? {});
        ensureHostAllowed(parsed.url, config);
        const args = ["-severity", "info,low", "-tags", "info,misconfiguration", "-target", parsed.url];
        if (parsed.tags && parsed.tags.length > 0) {
          const allowed = new Set(["info", "misconfiguration"]);
          for (const tag of parsed.tags) {
            if (allowed.has(tag)) {
              allowed.add(tag);
            }
          }
          args[3] = Array.from(allowed).join(",");
        }
        if (config.nucleiTemplatesDir) {
          args.push("-t", config.nucleiTemplatesDir);
        }
        const result = await runCommand("nuclei_safe", "nuclei", args, config);
        return { ...result };
      },
    });
  }

  if (scriptMap.size > 0) {
    const schema: ToolInputSchema = {
      zod: z.object({
        name: z.string(),
        args: z.array(z.string()).optional(),
      }),
      json: {
        type: "object",
        properties: {
          name: { type: "string", description: "Discovered script tool name (e.g., sh_audio_split)." },
          args: {
            type: "array",
            items: { type: "string" },
            description: "Arguments forwarded to the script.",
          },
        },
        required: ["name"],
      },
    };

    tools.push({
      name: "run_script",
      description: "Execute a discovered Toolhub script by name.",
      schema,
      handler: async (input: unknown) => {
        limiter.check("run_script");
        const parsed = schema.zod.parse(input ?? {});
        const script = scriptMap.get(parsed.name);
        if (!script) {
          throw new SecurityError("unknown_script", `Script ${parsed.name} is not registered.`);
        }
        const args = normaliseArgs(parsed.args);
        const result = await runCommand(
          "run_script",
          script.command,
          [...script.args, ...args],
          config,
        );
        return { ...result };
      },
    });
  }

  return tools;
}

function buildCliArgsFromObject(value: Record<string, unknown>, excludedKeys: Set<string>): string[] {
  const args: string[] = [];
  for (const [key, raw] of Object.entries(value)) {
    if (excludedKeys.has(key)) {
      continue;
    }
    if (raw === undefined || raw === null) {
      continue;
    }
    if (typeof raw === "boolean") {
      if (raw) {
        args.push(`--${normaliseFlag(key)}`);
      }
      continue;
    }
    if (Array.isArray(raw)) {
      for (const item of raw) {
        if (item === undefined || item === null) {
          continue;
        }
        args.push(`--${normaliseFlag(key)}`);
        args.push(String(item));
      }
      continue;
    }
    args.push(`--${normaliseFlag(key)}`);
    args.push(String(raw));
  }
  return args;
}

function normaliseFlag(key: string): string {
  return key
    .replace(/([a-z0-9])([A-Z])/g, "$1-$2")
    .replace(/_/g, "-")
    .toLowerCase();
}

async function resolveExecutable(commands: string[]): Promise<string | null> {
  for (const command of commands) {
    if (await hasExecutable(command)) {
      return command;
    }
  }
  return null;
}

async function hasExecutable(command: string): Promise<boolean> {
  const pathEnv = process.env.PATH ?? "";
  const segments = pathEnv.split(path.delimiter).filter(Boolean);
  for (const segment of segments) {
    const candidate = path.join(segment, command);
    try {
      await fs.access(candidate, fsConstants.X_OK);
      return true;
    } catch (error) {
      continue;
    }
  }
  return false;
}
