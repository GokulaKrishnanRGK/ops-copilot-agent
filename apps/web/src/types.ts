export type Session = {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
};

export type SessionListResponse = {
  items: Session[];
};

export type Message = {
  id: string;
  session_id: string;
  role: string;
  content: string;
  created_at: string;
  metadata_json: Record<string, unknown> | null;
};

export type MessageListResponse = {
  items: Message[];
};

export type UsageMetrics = {
  tokens_input: number;
  tokens_output: number;
  tokens_total: number;
  cost_usd: number;
  llm_call_count: number;
};

export type BudgetMetrics = {
  total_usd: number;
  delta_usd: number;
  event_count: number;
};

export type NodeUsage = {
  agent_node: string;
  tokens_input: number;
  tokens_output: number;
  tokens_total: number;
  cost_usd: number;
  llm_call_count: number;
};

export type RunMetrics = {
  usage: UsageMetrics;
  budget: BudgetMetrics;
  node_usage: NodeUsage[];
};

export type Run = {
  id: string;
  session_id: string;
  started_at: string;
  ended_at: string | null;
  status: string;
  config_json: Record<string, unknown>;
  metrics: RunMetrics;
};

export type SessionMetrics = {
  usage: UsageMetrics;
  budget: BudgetMetrics;
  run_count: number;
};

export type RunListResponse = {
  items: Run[];
  session_metrics: SessionMetrics;
};

export type ToolCall = {
  id: string;
  agent_run_id: string;
  tool_name: string;
  status: string;
  latency_ms: number;
  bytes_returned: number;
  truncated: boolean;
  error_message: string | null;
  created_at: string;
  log_text: string | null;
};

export type ToolCallListResponse = {
  items: ToolCall[];
};

export type ChatEvent = {
  type: string;
  timestamp: string;
  session_id: string;
  agent_run_id: string;
  payload: Record<string, unknown>;
};

export type TimelineItem = {
  id: string;
  label: string;
  detail: string;
};

export type ThemeMode = "system" | "dark" | "light";
