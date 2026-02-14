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
