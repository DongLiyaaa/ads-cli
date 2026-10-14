import type { Account, MCPToken } from "./types";

export function stamp(s?: string | null) {
  return s
    ? new Date(s).toLocaleString("zh-CN", { hour12: false })
    : "尚无记录";
}

export function accountName(accounts: Account[], id: string) {
  return accounts.find((a) => a.id === id)?.label || id.slice(0, 8);
}

export function tokenState(t: MCPToken) {
  if (t.revoked) return { tone: "cancelled", label: "已撤销" };
  if (new Date(t.expires_at) < new Date())
    return { tone: "failed", label: "已过期" };
  return { tone: "succeeded", label: "有效" };
}

/** Inclusive day count between two YYYY-MM-DD strings, or null if incomplete. */
export function daySpan(start: string, end: string) {
  if (!start || !end) return null;
  const ms = Date.parse(end + "T00:00:00Z") - Date.parse(start + "T00:00:00Z");
  return Number.isNaN(ms) ? null : Math.round(ms / 86400000) + 1;
}

export function parseArguments(text: string): {
  value?: Record<string, unknown>;
  error?: string;
} {
  try {
    const value = JSON.parse(text);
    if (!value || Array.isArray(value) || typeof value !== "object")
      return { error: "参数必须是 JSON 对象，例如 {}" };
    return { value };
  } catch (e) {
    return { error: "JSON 格式有误：" + (e as Error).message };
  }
}
