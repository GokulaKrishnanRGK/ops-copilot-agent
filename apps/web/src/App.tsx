import { FormEvent, UIEvent, useEffect, useMemo, useRef, useState } from "react";
import { ChatPanel, LiveEvent, RenderMessage } from "./components/ChatPanel";
import { buildChatTranscript } from "./components/ChatTranscript";
import { SessionsPanel } from "./components/SessionsPanel";
import { ThemeSelector } from "./components/ThemeSelector";
import { UsageDetailsModal } from "./components/UsageDetailsModal";
import { UsageSummary } from "./components/UsageSummary";
import { streamChat } from "./lib/sse";
import { useLazyListMessagesQuery } from "./store/api/messageApi";
import { useListRunsQuery } from "./store/api/runApi";
import { useLazyListToolCallsQuery } from "./store/api/toolCallApi";
import {
  sessionStreamUrl,
  useCreateSessionMutation,
  useDeleteSessionMutation,
  useLazyListSessionsQuery,
  useRenameSessionMutation,
} from "./store/api/sessionApi";
import { ChatEvent, Message, NodeUsage, Session, ThemeMode, ToolCall } from "./types";

const THEME_STORAGE_KEY = "opscopilot-theme-mode";
const SESSION_SCROLL_BATCH_SIZE = 5;
const CHAT_PAGE_SIZE = 5;

type StreamLogEvent = {
  runId: string;
  messages: RenderMessage[];
};

function normalizeMutationError(error: unknown, fallback: string): string {
  if (
    error &&
    typeof error === "object" &&
    "status" in error &&
    typeof (error as { status?: unknown }).status === "number"
  ) {
    return `${fallback} (${String((error as { status: number }).status)})`;
  }
  return fallback;
}

function errorMessageFromUnknown(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

function initialSessionPageSizeFromViewport(): number {
  if (typeof window === "undefined") {
    return 12;
  }
  const rowHeight = 42;
  const listHeight = Math.max(window.innerHeight - 260, 220);
  return Math.max(5, Math.floor(listHeight / rowHeight));
}

function streamSourceFromEvent(event: ChatEvent): string {
  const source = event.payload.source;
  if (typeof source === "string" && source.trim()) {
    return source.trim();
  }
  return "answer";
}

function stageFromEventType(
  eventType: string
): { stage: string; state: "running" | "done" } | null {
  if (eventType.endsWith(".started")) {
    return {
      stage: eventType.replace(".started", ""),
      state: "running",
    };
  }
  if (eventType.endsWith(".completed")) {
    return {
      stage: eventType.replace(".completed", ""),
      state: "done",
    };
  }
  return null;
}

function stageLabel(stage: string): string {
  const labels: Record<string, string> = {
    agent_run: "Run",
    scope_check: "Scope check",
    planner: "Planning",
    clarifier: "Clarification",
    answer: "Answering",
  };
  return labels[stage] ?? stage;
}

function streamLogMessagesFromEvent(event: ChatEvent): StreamLogEvent | null {
  if (event.type !== "tool.logs.available") {
    return null;
  }
  const itemsRaw = event.payload.items;
  if (!Array.isArray(itemsRaw)) {
    return null;
  }
  const runId = typeof event.agent_run_id === "string" ? event.agent_run_id : "";
  const messages = itemsRaw
    .map((raw, index) => {
      if (!raw || typeof raw !== "object") {
        return null;
      }
      const values = raw as Record<string, unknown>;
      if (values.tool_name !== "k8s.get_pod_logs") {
        return null;
      }
      const text = values.text;
      if (typeof text !== "string" || !text.trim()) {
        return null;
      }
      const stepId = values.step_id;
      const stepLabel = typeof stepId === "string" ? stepId : `item-${index}`;
      const truncated = Boolean(values.truncated);
      return {
        id: `log-${event.agent_run_id}-${stepLabel}-${index}`,
        role: "log" as const,
        text: truncated ? `${text}\n\n[truncated]` : text,
      };
    })
    .filter((item): item is RenderMessage => item !== null);
  return { runId, messages };
}

export function App() {
  const [fetchSessionsPage, { isFetching: isFetchingSessions, error: sessionsError }] =
    useLazyListSessionsQuery();
  const [createSession, { isLoading: isCreatingSession }] = useCreateSessionMutation();
  const [renameSession, { isLoading: isRenamingSession }] = useRenameSessionMutation();
  const [deleteSession, { isLoading: isDeletingSession }] = useDeleteSessionMutation();

  const [sessions, setSessions] = useState<Session[]>([]);
  const [hasMoreSessions, setHasMoreSessions] = useState<boolean>(true);
  const [initialSessionPageSize, setInitialSessionPageSize] = useState<number>(
    initialSessionPageSizeFromViewport
  );

  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [editingSessionId, setEditingSessionId] = useState<string>("");
  const [editingTitle, setEditingTitle] = useState<string>("");
  const [openMenuSessionId, setOpenMenuSessionId] = useState<string>("");

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showUsageDetails, setShowUsageDetails] = useState<boolean>(false);
  const [persistedMessages, setPersistedMessages] = useState<Message[]>([]);
  const [persistedToolCalls, setPersistedToolCalls] = useState<ToolCall[]>([]);
  const [messagesOffset, setMessagesOffset] = useState<number>(0);
  const [hasMoreMessages, setHasMoreMessages] = useState<boolean>(true);
  const [loadingOlderMessages, setLoadingOlderMessages] = useState<boolean>(false);
  const [streamMessages, setStreamMessages] = useState<RenderMessage[]>([]);
  const [pendingRunLogs, setPendingRunLogs] = useState<Record<string, RenderMessage[]>>({});
  const [activeRunId, setActiveRunId] = useState<string>("");
  const pendingRunLogsRef = useRef<Record<string, RenderMessage[]>>({});
  const activeRunIdRef = useRef<string>("");
  const loadedToolRunIdsRef = useRef<Set<string>>(new Set<string>());
  const shouldAutoScrollRef = useRef<boolean>(true);
  const scrollRestoreRef = useRef<{ previousTop: number; previousHeight: number } | null>(null);
  const [liveEvent, setLiveEvent] = useState<LiveEvent | null>(null);
  const [error, setError] = useState<string>("");
  const messagesContainerRef = useRef<HTMLDivElement | null>(null);

  const [themeMode, setThemeMode] = useState<ThemeMode>(() => {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "dark" || stored === "light" || stored === "system") {
      return stored;
    }
    return "system";
  });

  const [fetchMessagesPage, { error: messagesError }] = useLazyListMessagesQuery();
  const [fetchToolCallsByRunIds] = useLazyListToolCallsQuery();
  const {
    data: runsData,
    error: runsError,
    isFetching: isFetchingRuns,
    refetch: refetchRuns,
  } = useListRunsQuery(
    { sessionId: activeSessionId },
    {
      skip: !activeSessionId,
      refetchOnMountOrArgChange: true,
    }
  );

  useEffect(() => {
    if (!activeSessionId && sessions.length > 0) {
      setActiveSessionId(sessions[0].id);
      return;
    }
    if (activeSessionId && !sessions.some((session) => session.id === activeSessionId)) {
      setActiveSessionId(sessions[0]?.id ?? "");
      setStreamMessages([]);
      setLiveEvent(null);
    }
  }, [sessions, activeSessionId]);

  useEffect(() => {
    if (editingSessionId && !sessions.some((session) => session.id === editingSessionId)) {
      setEditingSessionId("");
      setEditingTitle("");
    }
  }, [sessions, editingSessionId]);

  function runIdsFromMessages(messages: Message[]): string[] {
    const ids = new Set<string>();
    for (const message of messages) {
      const metadata = message.metadata_json;
      if (!metadata || typeof metadata !== "object") {
        continue;
      }
      const runIdValue = metadata["run_id"];
      if (typeof runIdValue === "string" && runIdValue) {
        ids.add(runIdValue);
      }
    }
    return Array.from(ids);
  }

  function mergeToolCalls(existing: ToolCall[], incoming: ToolCall[]): ToolCall[] {
    if (incoming.length === 0) {
      return existing;
    }
    const seen = new Set(existing.map((item) => item.id));
    const next = [...existing];
    for (const item of incoming) {
      if (!seen.has(item.id)) {
        seen.add(item.id);
        next.push(item);
      }
    }
    return next;
  }

  async function loadToolCallsForMessages(messages: Message[]): Promise<void> {
    const allRunIds = runIdsFromMessages(messages);
    const runIdsToLoad = allRunIds.filter((runId) => !loadedToolRunIdsRef.current.has(runId));
    if (runIdsToLoad.length === 0) {
      return;
    }
    const toolCalls = await fetchToolCallsByRunIds({ runIds: runIdsToLoad }).unwrap();
    for (const runId of runIdsToLoad) {
      loadedToolRunIdsRef.current.add(runId);
    }
    setPersistedToolCalls((prev) => mergeToolCalls(prev, toolCalls));
  }

  async function loadMessagePage(options: {
    reset: boolean;
    preserveScroll: boolean;
  }): Promise<void> {
    if (!activeSessionId || loadingOlderMessages) {
      return;
    }
    if (options.preserveScroll) {
      const container = messagesContainerRef.current;
      if (container) {
        scrollRestoreRef.current = {
          previousTop: container.scrollTop,
          previousHeight: container.scrollHeight,
        };
      }
    }
    setLoadingOlderMessages(true);
    try {
      const offset = options.reset ? 0 : messagesOffset;
      const messages = await fetchMessagesPage({
        sessionId: activeSessionId,
        limit: CHAT_PAGE_SIZE,
        offset,
        order: "desc",
      }).unwrap();
      const chronological = [...messages].reverse();
      setHasMoreMessages(messages.length === CHAT_PAGE_SIZE);
      setMessagesOffset(offset + messages.length);
      if (options.reset) {
        setPersistedMessages(chronological);
      } else {
        setPersistedMessages((prev) => [...chronological, ...prev]);
      }
      await loadToolCallsForMessages(chronological);
    } catch (err) {
      scrollRestoreRef.current = null;
      setError(errorMessageFromUnknown(err, "list messages failed"));
    } finally {
      setLoadingOlderMessages(false);
    }
  }

  useEffect(() => {
    setOpenMenuSessionId("");
    setPersistedMessages([]);
    setPersistedToolCalls([]);
    setMessagesOffset(0);
    setHasMoreMessages(true);
    loadedToolRunIdsRef.current = new Set<string>();
    shouldAutoScrollRef.current = true;
    scrollRestoreRef.current = null;
    setStreamMessages([]);
    setPendingRunLogs({});
    pendingRunLogsRef.current = {};
    setActiveRunId("");
    activeRunIdRef.current = "";
    setLiveEvent(null);
    setShowUsageDetails(false);
  }, [activeSessionId]);

  useEffect(() => {
    if (!activeSessionId) {
      return;
    }
    void loadMessagePage({ reset: true, preserveScroll: false });
  }, [activeSessionId]);

  useEffect(() => {
    if (!activeSessionId || loadingOlderMessages || !hasMoreMessages) {
      return;
    }
    if (persistedMessages.length === 0) {
      return;
    }
    const container = messagesContainerRef.current;
    if (!container) {
      return;
    }
    const isScrollable = container.scrollHeight > container.clientHeight + 4;
    if (isScrollable) {
      return;
    }
    void loadMessagePage({ reset: false, preserveScroll: false });
  }, [activeSessionId, hasMoreMessages, loadingOlderMessages, persistedMessages.length]);

  useEffect(() => {
    pendingRunLogsRef.current = pendingRunLogs;
  }, [pendingRunLogs]);

  useEffect(() => {
    activeRunIdRef.current = activeRunId;
  }, [activeRunId]);

  useEffect(() => {
    function onResize() {
      setInitialSessionPageSize(initialSessionPageSizeFromViewport());
    }
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
    };
  }, []);

  useEffect(() => {
    window.localStorage.setItem(THEME_STORAGE_KEY, themeMode);
    if (themeMode === "system") {
      document.documentElement.removeAttribute("data-theme");
      return;
    }
    document.documentElement.setAttribute("data-theme", themeMode);
  }, [themeMode]);

  useEffect(() => {
    function onWindowClick() {
      setOpenMenuSessionId("");
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpenMenuSessionId("");
      }
    }

    window.addEventListener("click", onWindowClick);
    window.addEventListener("keydown", onKeyDown);

    return () => {
      window.removeEventListener("click", onWindowClick);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  useEffect(() => {
    void loadSessionsPage({ offset: 0, limit: initialSessionPageSize, replace: true });
  }, [initialSessionPageSize]);

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) ?? null,
    [sessions, activeSessionId]
  );

  const chatMessages = useMemo(
    () => buildChatTranscript(persistedMessages, persistedToolCalls, streamMessages),
    [persistedMessages, persistedToolCalls, streamMessages]
  );
  const latestRun = useMemo(() => runsData?.items[0] ?? null, [runsData]);
  const sessionNodeUsage = useMemo<NodeUsage[]>(() => {
    const items = runsData?.items ?? [];
    const nodeMap = new Map<string, NodeUsage>();
    for (const run of items) {
      for (const node of run.metrics.node_usage) {
        const existing = nodeMap.get(node.agent_node);
        if (!existing) {
          nodeMap.set(node.agent_node, { ...node });
          continue;
        }
        nodeMap.set(node.agent_node, {
          agent_node: node.agent_node,
          tokens_input: existing.tokens_input + node.tokens_input,
          tokens_output: existing.tokens_output + node.tokens_output,
          tokens_total: existing.tokens_total + node.tokens_total,
          cost_usd: existing.cost_usd + node.cost_usd,
          llm_call_count: existing.llm_call_count + node.llm_call_count,
        });
      }
    }
    return Array.from(nodeMap.values()).sort((a, b) => b.cost_usd - a.cost_usd);
  }, [runsData]);

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) {
      return;
    }

    const restore = scrollRestoreRef.current;
    if (restore) {
      const nextTop = container.scrollHeight - restore.previousHeight + restore.previousTop;
      container.scrollTop = nextTop;
      scrollRestoreRef.current = null;
      return;
    }

    if (!shouldAutoScrollRef.current) {
      return;
    }

    container.scrollTop = container.scrollHeight;
  }, [chatMessages, liveEvent, loading]);

  const sessionsErrorMessage = sessionsError ? "list sessions failed" : "";
  const messagesErrorMessage = messagesError ? "list messages failed" : "";
  const runsErrorMessage = runsError ? "list runs failed" : "";
  const displayError = error || sessionsErrorMessage || messagesErrorMessage || runsErrorMessage;

  async function loadSessionsPage(options: {
    offset: number;
    limit: number;
    replace: boolean;
  }): Promise<void> {
    if (isFetchingSessions) {
      return;
    }
    const items = await fetchSessionsPage({
      offset: options.offset,
      limit: options.limit,
    }).unwrap();
    setHasMoreSessions(items.length === options.limit);
    setSessions((prev) => (options.replace ? items : [...prev, ...items]));
  }

  async function onCreateSession() {
    setError("");
    try {
      const created = await createSession({ title: `Session ${sessions.length + 1}` }).unwrap();
      await loadSessionsPage({ offset: 0, limit: initialSessionPageSize, replace: true });
      setActiveSessionId(created.id);
      setEditingSessionId("");
      setEditingTitle("");
      setOpenMenuSessionId("");
      setStreamMessages([]);
      setLiveEvent(null);
    } catch (err) {
      setError(normalizeMutationError(err, "create session failed"));
    }
  }

  function onStartRename(session: Session) {
    setError("");
    setOpenMenuSessionId("");
    setEditingSessionId(session.id);
    setEditingTitle(session.title ?? "");
  }

  function onCancelRename() {
    setEditingSessionId("");
    setEditingTitle("");
  }

  async function onSaveRename(sessionId: string) {
    const nextTitle = editingTitle.trim();
    if (!nextTitle) {
      setError("session title is required");
      return;
    }

    setError("");
    try {
      await renameSession({ sessionId, title: nextTitle }).unwrap();
      await loadSessionsPage({
        offset: 0,
        limit: sessions.length || initialSessionPageSize,
        replace: true,
      });
      setEditingSessionId("");
      setEditingTitle("");
    } catch (err) {
      setError(normalizeMutationError(err, "rename session failed"));
    }
  }

  async function onDeleteSession(sessionId: string) {
    setError("");
    setOpenMenuSessionId("");
    try {
      await deleteSession({ sessionId }).unwrap();
      await loadSessionsPage({
        offset: 0,
        limit: Math.max(sessions.length, initialSessionPageSize),
        replace: true,
      });
      if (sessionId === activeSessionId) {
        setActiveSessionId("");
        setStreamMessages([]);
        setLiveEvent(null);
      }
      if (sessionId === editingSessionId) {
        setEditingSessionId("");
        setEditingTitle("");
      }
    } catch (err) {
      setError(normalizeMutationError(err, "delete session failed"));
    }
  }

  function onSessionListScroll(event: UIEvent<HTMLUListElement>) {
    if (!hasMoreSessions || isFetchingSessions) {
      return;
    }
    const target = event.currentTarget;
    const nearBottom = target.scrollTop + target.clientHeight >= target.scrollHeight - 64;
    if (!nearBottom) {
      return;
    }
    void loadSessionsPage({
      offset: sessions.length,
      limit: SESSION_SCROLL_BATCH_SIZE,
      replace: false,
    });
  }

  function onChatMessagesScroll(event: UIEvent<HTMLDivElement>) {
    const target = event.currentTarget;
    const nearBottom = target.scrollTop + target.clientHeight >= target.scrollHeight - 16;
    shouldAutoScrollRef.current = nearBottom;

    const nearTop = target.scrollTop <= 24;
    if (!nearTop || !hasMoreMessages || loadingOlderMessages) {
      return;
    }

    void loadMessagePage({ reset: false, preserveScroll: true });
  }

  function insertLogsAfterAssistantMessage(
    messages: RenderMessage[],
    assistantMessageId: string,
    logs: RenderMessage[]
  ): RenderMessage[] {
    if (logs.length === 0) {
      return messages;
    }
    const assistantIndex = messages.findIndex((item) => item.id === assistantMessageId);
    if (assistantIndex === -1) {
      return messages;
    }
    const existingIds = new Set(messages.map((item) => item.id));
    const dedupedLogs = logs.filter((log) => !existingIds.has(log.id));
    if (dedupedLogs.length === 0) {
      return messages;
    }
    const next = [...messages];
    next.splice(assistantIndex + 1, 0, ...dedupedLogs);
    return next;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!activeSessionId || !input.trim()) {
      return;
    }

    setError("");
    setLiveEvent(null);
    const userText = input.trim();
    setInput("");

    const streamId = `${Date.now()}`;
    const userMessageId = `temp-user-${streamId}`;

    shouldAutoScrollRef.current = true;
    setStreamMessages((prev) => [...prev, { id: userMessageId, role: "user", text: userText }]);
    setLoading(true);

    try {
      const streamResult = await streamChat(
        sessionStreamUrl(activeSessionId),
        { message: userText },
        (chatEvent) => {
          if (chatEvent.type === "assistant.token.delta") {
            const text = String(chatEvent.payload.text ?? "");
            const source = streamSourceFromEvent(chatEvent);
            const assistantMessageId = `temp-assistant-${streamId}-${source}`;
            setStreamMessages((prev) => {
              const existingIndex = prev.findIndex((item) => item.id === assistantMessageId);
              if (existingIndex === -1) {
                return [...prev, { id: assistantMessageId, role: "assistant", text }];
              }
              const next = [...prev];
              const existing = next[existingIndex];
              next[existingIndex] = {
                ...existing,
                text: `${existing.text}${text}`,
              };
              return next;
            });
            return;
          }

          if (chatEvent.type === "tool.logs.available") {
            const logEvent = streamLogMessagesFromEvent(chatEvent);
            if (logEvent && logEvent.messages.length > 0 && logEvent.runId) {
              setPendingRunLogs((prev) => {
                const nextForRun = prev[logEvent.runId]
                  ? [...prev[logEvent.runId], ...logEvent.messages]
                  : [...logEvent.messages];
                const next = {
                  ...prev,
                  [logEvent.runId]: nextForRun,
                };
                pendingRunLogsRef.current = next;
                return next;
              });
            }
            if (logEvent && logEvent.messages.length > 0) {
              const assistantMessageId = `temp-assistant-${streamId}-answer`;
              setStreamMessages((prev) =>
                insertLogsAfterAssistantMessage(prev, assistantMessageId, logEvent.messages)
              );
            }
            return;
          }

          if (chatEvent.type === "agent_run.started") {
            if (typeof chatEvent.agent_run_id === "string" && chatEvent.agent_run_id) {
              setActiveRunId(chatEvent.agent_run_id);
              activeRunIdRef.current = chatEvent.agent_run_id;
            }
          }

          const stage = stageFromEventType(chatEvent.type);
          if (stage) {
            setLiveEvent({
              id: stage.stage,
              label: stageLabel(stage.stage),
              state: stage.state,
            });
          }

          if (chatEvent.type === "answer.completed") {
            const finalMessage = chatEvent.payload.message;
            if (typeof finalMessage === "string" && finalMessage.trim()) {
              const assistantMessageId = `temp-assistant-${streamId}-answer`;
              const runId =
                activeRunIdRef.current ||
                (typeof chatEvent.agent_run_id === "string" ? chatEvent.agent_run_id : "");
              const logsForRun = runId ? (pendingRunLogsRef.current[runId] ?? []) : [];
              setStreamMessages((prev) => {
                const existingIndex = prev.findIndex((item) => item.id === assistantMessageId);
                if (existingIndex === -1) {
                  const nextWithAssistant = [
                    ...prev,
                    { id: assistantMessageId, role: "assistant", text: finalMessage },
                  ];
                  return insertLogsAfterAssistantMessage(
                    nextWithAssistant,
                    assistantMessageId,
                    logsForRun
                  );
                }
                const next = [...prev];
                next[existingIndex] = {
                  ...next[existingIndex],
                  text: finalMessage,
                };
                return insertLogsAfterAssistantMessage(next, assistantMessageId, logsForRun);
              });
              if (runId && logsForRun.length > 0) {
                setPendingRunLogs((prev) => {
                  const next = { ...prev };
                  delete next[runId];
                  pendingRunLogsRef.current = next;
                  return next;
                });
              }
            }
            return;
          }

          if (chatEvent.type === "agent_run.completed") {
            const runId =
              typeof chatEvent.agent_run_id === "string" && chatEvent.agent_run_id
                ? chatEvent.agent_run_id
                : activeRunIdRef.current;
            if (runId) {
              const logsForRun = pendingRunLogsRef.current[runId] ?? [];
              if (logsForRun.length > 0) {
                const assistantMessageId = `temp-assistant-${streamId}-answer`;
                setStreamMessages((prev) =>
                  insertLogsAfterAssistantMessage(prev, assistantMessageId, logsForRun)
                );
                setPendingRunLogs((prev) => {
                  const next = { ...prev };
                  delete next[runId];
                  pendingRunLogsRef.current = next;
                  return next;
                });
              }
            }
            setLiveEvent(null);
            setActiveRunId("");
            activeRunIdRef.current = "";
            return;
          }

          if (chatEvent.type === "agent_run.failed") {
            setLiveEvent(null);
            setActiveRunId("");
            activeRunIdRef.current = "";
            const reason = chatEvent.payload.reason;
            if (typeof reason === "string" && reason.trim()) {
              setError(reason);
            }
            return;
          }

          if (chatEvent.type === "error") {
            const message = chatEvent.payload.message;
            if (typeof message === "string" && message.trim()) {
              setError(message);
            }
            setLiveEvent(null);
            setActiveRunId("");
            activeRunIdRef.current = "";
          }
        },
        {
          maxRetries: 2,
          retryDelayMs: 350,
          onRetry: (retryAttempt) => {
            setLiveEvent({
              id: "stream_retry",
              label: `Reconnecting stream (${retryAttempt})`,
              state: "running",
            });
          },
        }
      );
      if (!streamResult.terminalReceived) {
        setLiveEvent(null);
        setActiveRunId("");
        activeRunIdRef.current = "";
        setError("stream ended before a terminal event");
      }
    } catch (err) {
      setError(errorMessageFromUnknown(err, "request failed"));
      setLiveEvent(null);
      setActiveRunId("");
      activeRunIdRef.current = "";
    } finally {
      setLoading(false);
      void refetchRuns();
    }
  }

  return (
    <div className="page">
      <header className="masthead">
        <div className="masthead-copy">
          <h1>Ops Copilot</h1>
          <p>Live operations assistant with streaming execution trace</p>
        </div>
        <ThemeSelector value={themeMode} onChange={setThemeMode} />
      </header>
      <main className="layout">
        <SessionsPanel
          sessions={sessions}
          activeSessionId={activeSessionId}
          editingSessionId={editingSessionId}
          editingTitle={editingTitle}
          openMenuSessionId={openMenuSessionId}
          hasMoreSessions={hasMoreSessions}
          loadingState={{
            creating: isCreatingSession,
            renaming: isRenamingSession,
            deleting: isDeletingSession,
          }}
          onCreateSession={onCreateSession}
          onSelectSession={setActiveSessionId}
          onStartRename={onStartRename}
          onCancelRename={onCancelRename}
          onSaveRename={(sessionId) => {
            void onSaveRename(sessionId);
          }}
          onDeleteSession={(sessionId) => {
            void onDeleteSession(sessionId);
          }}
          onEditingTitleChange={setEditingTitle}
          onToggleSessionMenu={(sessionId) => {
            setOpenMenuSessionId((prev) => (prev === sessionId ? "" : sessionId));
          }}
          onSessionListScroll={onSessionListScroll}
        />
        <ChatPanel
          activeSessionLabel={
            activeSession ? activeSession.title || activeSession.id : "No session selected"
          }
          summary={
            <UsageSummary
              sessionMetrics={runsData?.sessionMetrics ?? null}
              latestRun={latestRun}
              loading={isFetchingRuns}
              onOpenDetails={() => {
                setShowUsageDetails(true);
              }}
            />
          }
          messages={chatMessages}
          liveEvent={liveEvent}
          input={input}
          loading={loading}
          disabled={!activeSessionId}
          error={displayError}
          messagesContainerRef={messagesContainerRef}
          onMessagesScroll={onChatMessagesScroll}
          onInputChange={setInput}
          onSubmit={(submitEvent) => {
            void onSubmit(submitEvent);
          }}
        />
      </main>
      <UsageDetailsModal
        isOpen={showUsageDetails}
        latestRun={latestRun}
        sessionNodeUsage={sessionNodeUsage}
        onClose={() => {
          setShowUsageDetails(false);
        }}
      />
    </div>
  );
}
