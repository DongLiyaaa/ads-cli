export type Account = {
  id: string;
  label: string;
  marketplace: string;
  profile_id: string;
  region: string;
  verified_at: string | null;
  currency?: string;
  timezone?: string;
  relay_id?: string | null;
};
export type ServerCheck = {
  key: string;
  label: string;
  ok: boolean;
  detail: string;
  required: boolean;
};
export type RelayServer = {
  id: string;
  name: string;
  host: string;
  ssh_port: number;
  username: string;
  auth_type: "key" | "password";
  relay_port: number;
  status: string;
  checks: ServerCheck[];
  message: string | null;
  host_fingerprint: string | null;
  installed: boolean;
  relay_version: string | null;
  checked_at: string | null;
  installed_at: string | null;
  created_at: string;
  accounts: { id: string; label: string }[];
  plan?: string[];
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
  /** AMC only: rows whose labels Amazon hid for privacy, and their share of each metric. */
  privacy?: AmcPrivacy;
};
export type AmcPrivacy = {
  rows: number;
  filtered_rows: number;
  merged: boolean;
  shares: Record<string, number>;
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
  created_at: string;
  expires_at: string;
  permanent: boolean;
  revoked: boolean;
  can_reveal: boolean;
  last_used_at: string | null;
};
export type LogEntry = {
  id: string;
  action: string;
  status: string;
  account_id: string | null;
  task_id: string | null;
  token_name: string | null;
  token_prefix: string | null;
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
export type SetupState = {
  needs_setup: boolean;
  token_required: boolean;
  available: boolean;
};
export type AmcColumn = {
  name: string;
  type: string;
  kind: string;
  description: string;
};
export type AmcSource = {
  id: string;
  description: string;
  tags: string[];
  premium: boolean;
  audienceOnly: boolean;
  columns: AmcColumn[];
};
export type AmcTemplate = {
  id: string;
  name: string;
  description: string;
  sources: string[];
  /** "full" templates export complete data; "analysis" ones answer one question. */
  category: "analysis" | "full";
  sql: string;
  sqlText: string;
};
export type AmcOverview = {
  available: boolean;
  reason?: string;
  instance?: {
    instanceId: string;
    instanceType?: string;
    creationStatus?: string;
    creationDatetime?: string;
    optionalDatasets: string[];
  };
  dataSources?: AmcSource[];
  templates: AmcTemplate[];
};
export type SummaryBlock = { rows: number; sums: Record<string, number | null> };
export type SummaryResult = {
  group_by: string | null;
  total: SummaryBlock;
  groups: (SummaryBlock & { key: string | null })[];
  truncated: boolean;
};
