export type Account = {
  id: string;
  label: string;
  marketplace: string;
  profile_id: string;
  region: string;
  verified_at: string | null;
  currency?: string;
  timezone?: string;
};
export type Task = {
  id: string;
  account_id: string;
  operation: string;
  kind: string;
  status: string;
  created_at: string;
  updated_at: string;
  row_count: number;
  remote_status?: string;
  remote_id?: string;
  error?: string;
  payload_hash: string;
  payload?: any;
  arguments?: any;
  result?: any;
  result_truncated?: boolean;
};
export type Capability = {
  operation: string;
  kind: string;
  description: string;
  inputSchema: {
    properties: Record<
      string,
      { type: string; default?: any; enum?: string[]; description: string }
    >;
    required: string[];
  };
};
export type MCPToken = {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  account_ids: string[];
  expires_at: string;
  revoked: boolean;
  last_used_at: string | null;
};
export type LogEntry = {
  id: string;
  action: string;
  status: string;
  account_id: string | null;
  task_id: string | null;
  detail: unknown;
  created_at: string;
};
export type Overview = {
  accounts?: number;
  tasks_by_status?: Record<string, number>;
  report_rows?: number;
  mcp_endpoint?: string;
  max_api_concurrency?: number;
};
export type RowsPage = { rows: any[]; total: number };
