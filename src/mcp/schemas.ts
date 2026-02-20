import { z } from "zod";

export interface JsonSchema {
  type?: string;
  properties?: Record<string, JsonSchema>;
  items?: JsonSchema;
  required?: string[];
  description?: string;
  enum?: string[];
  pattern?: string;
  additionalProperties?: boolean | JsonSchema;
}

export interface ToolInputSchema {
  zod: z.ZodTypeAny;
  json: JsonSchema;
}

export const DefaultArgsSchema: ToolInputSchema = {
  zod: z.object({
    args: z.array(z.string()).optional(),
  }),
  json: {
    type: "object",
    properties: {
      args: {
        type: "array",
        items: { type: "string" },
        description: "Positional arguments forwarded to the underlying script or CLI.",
      },
    },
  },
};

const BOOLEAN_STRINGS = new Set(["true", "false"]);

export function jsonSchemaToZod(schema: JsonSchema): z.ZodTypeAny {
  if (!schema || typeof schema !== "object") {
    return z.any();
  }

  switch (schema.type) {
    case "object": {
      const properties = schema.properties ?? {};
      const required = new Set(schema.required ?? []);
      const shape: Record<string, z.ZodTypeAny> = {};
      for (const [key, value] of Object.entries(properties)) {
        const propertySchema = jsonSchemaToZod(value);
        shape[key] = required.has(key) ? propertySchema : propertySchema.optional();
      }
      const base = z.object(shape);
      if (schema.additionalProperties === false) {
        return base.strict();
      }
      return base;
    }
    case "array": {
      const itemsSchema = schema.items ? jsonSchemaToZod(schema.items) : z.any();
      return z.array(itemsSchema);
    }
    case "string": {
      if (schema.enum && schema.enum.length > 0) {
        const [first, ...rest] = schema.enum;
        if (!first) {
          return z.string();
        }
        return z.enum([first, ...rest] as [string, ...string[]]);
      }
      if (schema.pattern) {
        try {
          // Keep JSON-schema string pattern constraints when converting to zod.
          return z.string().regex(new RegExp(schema.pattern));
        } catch {
          return z.string();
        }
      }
      return z.string();
    }
    case "number":
    case "integer":
      return z.number();
    case "boolean":
      return z.boolean();
    default:
      return z.any();
  }
}

export function normaliseArgs(args: string[] | undefined): string[] {
  if (!args) {
    return [];
  }
  return args.filter((entry) => typeof entry === "string" && entry.trim().length > 0);
}

export function coerceBoolean(value: string | undefined, fallback: boolean): boolean {
  if (value === undefined) {
    return fallback;
  }
  const normalised = value.trim().toLowerCase();
  if (BOOLEAN_STRINGS.has(normalised)) {
    return normalised === "true";
  }
  return fallback;
}

export function csvToList(value: string | undefined, fallback: string[]): string[] {
  if (!value) {
    return fallback;
  }
  return value
    .split(",")
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0);
}
