/** MCP connection details. Mirrors backend/app/api/v1/agent_docs.py. */

import { apiFetch } from './client';

export interface McpTool {
  readonly name: string;
  readonly summary: string;
}

export interface McpInfo {
  readonly url: string;
  /** Ready to paste. Generated from the settings the server binds to, never written twice. */
  readonly command: string;
  readonly tools: readonly McpTool[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isMcpInfo(value: unknown): value is McpInfo {
  return (
    isRecord(value) &&
    typeof value['url'] === 'string' &&
    typeof value['command'] === 'string' &&
    Array.isArray(value['tools'])
  );
}

export function fetchMcpInfo(signal?: AbortSignal): Promise<McpInfo> {
  return apiFetch('/docs/mcp', isMcpInfo, signal ? { signal } : undefined);
}
