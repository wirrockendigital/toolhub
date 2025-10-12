import path from "node:path";
import { McpConfig } from "./config.js";

const DESTRUCTIVE_PATTERNS = [
  /rm\s+-rf/i,
  /mkfs/i,
  /shutdown/i,
  /reboot/i,
  /:\(\)\s*\{\s*: \| : & \};\s*:/,
];

const NUCLEI_DENY_TAGS = ["cve", "rce", "dos", "exploit", "malware", "bruteforce", "takeover"];

export class SecurityError extends Error {
  public readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

export class RateLimiter {
  private readonly history = new Map<string, number[]>();

  constructor(private readonly maxCalls: number, private readonly windowMs: number) {}

  check(toolName: string): void {
    if (this.maxCalls <= 0) {
      return;
    }

    const now = Date.now();
    const windowStart = now - this.windowMs;
    const history = this.history.get(toolName) ?? [];
    const filtered = history.filter((timestamp) => timestamp >= windowStart);

    if (filtered.length >= this.maxCalls) {
      throw new SecurityError(
        "rate_limit",
        `Tool \"${toolName}\" is rate limited. Allowance resets in ${Math.ceil(
          (filtered[0] + this.windowMs - now) / 1000,
        )} seconds.`,
      );
    }

    filtered.push(now);
    this.history.set(toolName, filtered);
  }
}

export function ensurePathAllowed(inputPath: string, config: McpConfig): void {
  if (!inputPath) {
    return;
  }

  if (!inputPath.startsWith("/")) {
    // Relative paths are permitted to keep UX predictable; they will resolve against cwd later.
    return;
  }

  const resolved = path.resolve(inputPath);
  const allowed = config.allowlistPaths.some((prefix) => resolved.startsWith(path.resolve(prefix)));
  if (!allowed) {
    throw new SecurityError(
      "path_not_allowed",
      `Path ${resolved} is not inside the configured allowlist: ${config.allowlistPaths.join(", ")}.`,
    );
  }
}

export function ensureHostAllowed(target: string, config: McpConfig): void {
  if (!target) {
    return;
  }

  try {
    const url = new URL(target.includes("://") ? target : `http://${target}`);
    const hostname = url.hostname.toLowerCase();
    if (!config.allowlistHosts.some((host) => host.toLowerCase() === hostname)) {
      throw new SecurityError(
        "host_not_allowed",
        `Host ${hostname} is not allowlisted. Allowed hosts: ${config.allowlistHosts.join(", ")}.`,
      );
    }
  } catch (error) {
    // Non-URL strings are ignored.
  }
}

export function enforceSafeMode(toolName: string, command: string, args: string[], config: McpConfig): void {
  if (!config.safeMode) {
    return;
  }

  const joined = `${command} ${args.join(" ")}`;
  for (const pattern of DESTRUCTIVE_PATTERNS) {
    if (pattern.test(joined)) {
      throw new SecurityError("unsafe_command", `Command is blocked in safe-mode: pattern ${pattern}`);
    }
  }

  for (const candidate of args) {
    if (candidate.startsWith("/app/scripts")) {
      continue;
    }
    if (candidate.startsWith("/")) {
      ensurePathAllowed(candidate, config);
    }
    if (candidate.includes("://")) {
      ensureHostAllowed(candidate, config);
    }
  }

  if (toolName.startsWith("nuclei")) {
    enforceNucleiGuardrails(args);
  }
}

function enforceNucleiGuardrails(args: string[]): void {
  const lowerArgs = args.map((value) => value.toLowerCase());
  if (lowerArgs.some((value) => NUCLEI_DENY_TAGS.some((tag) => value.includes(tag)))) {
    throw new SecurityError("nuclei_denylist", "Requested nuclei templates include high-risk tags that are blocked.");
  }

  const hasSeverity = lowerArgs.some((value) => value.startsWith("-severity"));
  if (hasSeverity && !lowerArgs.some((value) => value.includes("info"))) {
    throw new SecurityError("nuclei_severity", "nuclei severity must include info or low only.");
  }

  if (!hasSeverity) {
    throw new SecurityError("nuclei_severity", "nuclei must specify -severity info,low in safe-mode.");
  }

  if (lowerArgs.some((value) => value.includes("high")) || lowerArgs.some((value) => value.includes("critical"))) {
    throw new SecurityError("nuclei_severity", "nuclei high/critical severities are disabled in safe-mode.");
  }
}

export function truncateOutput(text: string, maxLength: number): { output: string; truncated: boolean } {
  if (text.length <= maxLength) {
    return { output: text, truncated: false };
  }
  return {
    output: `${text.slice(0, maxLength)}\n[output truncated]`,
    truncated: true,
  };
}
