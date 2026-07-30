/** snake_case ↔ camelCase conversion at the API boundary only. */

function toCamelKey(key: string): string {
  return key.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
}

function toSnakeKey(key: string): string {
  return key.replace(/[A-Z]/g, (c) => `_${c.toLowerCase()}`);
}

/** Permission map keys like `hr_admin.cv_screening` are opaque — do not camelCase them. */
function shouldPreserveKey(key: string): boolean {
  return key.includes(".");
}

export function keysToCamel<T>(input: unknown): T {
  if (Array.isArray(input)) {
    return input.map((item) => keysToCamel(item)) as T;
  }
  if (input !== null && typeof input === "object" && !(input instanceof Date)) {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(input as Record<string, unknown>)) {
      const nextKey = shouldPreserveKey(k) ? k : toCamelKey(k);
      out[nextKey] = keysToCamel(v);
    }
    return out as T;
  }
  return input as T;
}

export function keysToSnake(input: unknown): unknown {
  if (Array.isArray(input)) {
    return input.map((item) => keysToSnake(item));
  }
  if (input !== null && typeof input === "object" && !(input instanceof Date)) {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(input as Record<string, unknown>)) {
      const nextKey = shouldPreserveKey(k) ? k : toSnakeKey(k);
      out[nextKey] = keysToSnake(v);
    }
    return out;
  }
  return input;
}

export const PERMISSION_RANK: Record<string, number> = {
  none: 0,
  read: 1,
  write: 2,
  approve: 3,
  admin: 4,
};

export const AGENT_KEY = "hr_admin";
