import { Message, ToolCall } from "../types";
import { RenderMessage } from "./ChatPanel";

type PersistedChatMessage = RenderMessage & {
  runId: string;
  role: "user" | "assistant";
};

type PersistedLogMessage = RenderMessage & {
  runId: string;
  role: "log";
};

function mapPersistedMessageWithRun(message: Message): PersistedChatMessage {
  const role = message.role === "user" ? "user" : "assistant";
  const metadata = message.metadata_json;
  const runIdValue =
    metadata && typeof metadata === "object" ? (metadata["run_id"] as unknown) : undefined;
  const runId = typeof runIdValue === "string" ? runIdValue : "";
  return {
    id: message.id,
    role,
    text: message.content,
    runId,
  };
}

function normalizedMessages(messages: PersistedChatMessage[]): PersistedChatMessage[] {
  const output: PersistedChatMessage[] = [];
  let pendingUserRunId = "";
  for (const message of messages) {
    if (message.role === "user") {
      pendingUserRunId = message.runId;
      output.push(message);
      continue;
    }
    if (message.role === "assistant" && !message.runId && pendingUserRunId) {
      output.push({ ...message, runId: pendingUserRunId });
      pendingUserRunId = "";
      continue;
    }
    output.push(message);
    if (message.role === "assistant") {
      pendingUserRunId = "";
    }
  }
  return output;
}

function persistedLogMessages(toolCalls: ToolCall[]): PersistedLogMessage[] {
  return toolCalls
    .filter((item) => item.tool_name === "k8s.get_pod_logs")
    .map((item) => {
      if (typeof item.log_text !== "string" || !item.log_text.trim()) {
        return null;
      }
      return {
        id: `persisted-log-${item.id}`,
        role: "log" as const,
        text: item.truncated ? `${item.log_text}\n\n[truncated]` : item.log_text,
        runId: item.agent_run_id,
      };
    })
    .filter((item): item is PersistedLogMessage => item !== null);
}

export function buildChatTranscript(
  persistedMessages: Message[],
  persistedToolCalls: ToolCall[],
  streamMessages: RenderMessage[]
): RenderMessage[] {
  const mappedMessages = normalizedMessages(persistedMessages.map(mapPersistedMessageWithRun));
  const logsByRun = new Map<string, PersistedLogMessage[]>();
  for (const log of persistedLogMessages(persistedToolCalls)) {
    if (!log.runId) {
      continue;
    }
    const next = logsByRun.get(log.runId) ?? [];
    next.push(log);
    logsByRun.set(log.runId, next);
  }

  const merged: RenderMessage[] = [];
  for (const message of mappedMessages) {
    merged.push({ id: message.id, role: message.role, text: message.text });
    if (message.role === "assistant" && message.runId) {
      const logs = logsByRun.get(message.runId) ?? [];
      for (const log of logs) {
        merged.push({ id: log.id, role: "log", text: log.text });
      }
      logsByRun.delete(message.runId);
    }
  }

  // If any logs still cannot be matched by run_id, keep them visible near the end
  // instead of silently dropping them.
  for (const orphanLogs of logsByRun.values()) {
    for (const log of orphanLogs) {
      merged.push({ id: `${log.id}-orphan`, role: "log", text: log.text });
    }
  }

  return [...merged, ...streamMessages];
}
