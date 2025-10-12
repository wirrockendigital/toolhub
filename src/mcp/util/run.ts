import { execa } from "execa";
import { McpConfig } from "../config.js";
import { enforceSafeMode, truncateOutput } from "../security.js";

export interface RunCommandOptions {
  env?: NodeJS.ProcessEnv;
  cwd?: string;
  timeoutMs?: number;
}

export interface CommandResult {
  exitCode: number;
  output: string;
  truncated: boolean;
}

export async function runCommand(
  toolName: string,
  command: string,
  args: string[],
  config: McpConfig,
  options: RunCommandOptions = {},
): Promise<CommandResult> {
  enforceSafeMode(toolName, command, args, config);

  const subprocess = execa(command, args, {
    all: true,
    reject: false,
    env: options.env,
    cwd: options.cwd,
    timeout: options.timeoutMs ?? config.commandTimeoutMs,
  });

  const result = await subprocess;
  const combined = result.all ?? [result.stdout, result.stderr].filter(Boolean).join("\n");
  const { output, truncated } = truncateOutput(combined, config.maxOutputLength);

  if (result.exitCode !== 0) {
    return {
      exitCode: result.exitCode,
      output: `Command exited with code ${result.exitCode}.\n${output}`.trim(),
      truncated,
    };
  }

  return {
    exitCode: result.exitCode,
    output,
    truncated,
  };
}
