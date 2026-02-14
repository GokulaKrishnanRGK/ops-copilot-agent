import { FormEvent, UIEvent, useEffect, useMemo, useRef, useState } from "react";
import { ChatPanel, LiveEvent, RenderMessage } from "./components/ChatPanel";
import { SessionsPanel } from "./components/SessionsPanel";
import { ThemeSelector } from "./components/ThemeSelector";
import { UsageDetailsModal } from "./components/UsageDetailsModal";
import { UsageSummary } from "./components/UsageSummary";
import { streamChat } from "./lib/sse";
import { useListMessagesQuery } from "./store/api/messageApi";
import { useListRunsQuery } from "./store/api/runApi";
import {
  sessionStreamUrl,
  useCreateSessionMutation,
  useDeleteSessionMutation,
  useLazyListSessionsQuery,
  useRenameSessionMutation,
} from "./store/api/sessionApi";
import { ChatEvent, Message, NodeUsage, Session, ThemeMode } from "./types";

const THEME_STORAGE_KEY = "opscopilot-theme-mode";
const SESSION_SCROLL_BATCH_SIZE = 5;

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

function mapPersistedMessage(message: Message): RenderMessage {
  const role = message.role === "user" ? "user" : "assistant";
  return {
    id: message.id,
    role,
    text: message.content,
  };
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
  const [streamMessages, setStreamMessages] = useState<RenderMessage[]>([]);
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

  const { data: persistedMessages = [], error: messagesError } = useListMessagesQuery(
    { sessionId: activeSessionId },
    {
      skip: !activeSessionId,
      refetchOnMountOrArgChange: true,
    }
  );
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

  useEffect(() => {
    setOpenMenuSessionId("");
    setStreamMessages([]);
    setLiveEvent(null);
    setShowUsageDetails(false);
  }, [activeSessionId]);

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

  const chatMessages = useMemo(() => {
    const persisted = persistedMessages.map(mapPersistedMessage);
    return [...persisted, ...streamMessages];
  }, [persistedMessages, streamMessages]);
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

    setStreamMessages((prev) => [...prev, { id: userMessageId, role: "user", text: userText }]);
    setLoading(true);

    try {
      await streamChat(sessionStreamUrl(activeSessionId), { message: userText }, (chatEvent) => {
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
            setStreamMessages((prev) => {
              const existingIndex = prev.findIndex((item) => item.id === assistantMessageId);
              if (existingIndex === -1) {
                return [...prev, { id: assistantMessageId, role: "assistant", text: finalMessage }];
              }
              const next = [...prev];
              next[existingIndex] = {
                ...next[existingIndex],
                text: finalMessage,
              };
              return next;
            });
          }
          return;
        }

        if (chatEvent.type === "agent_run.completed") {
          setLiveEvent(null);
          return;
        }

        if (chatEvent.type === "agent_run.failed") {
          setLiveEvent(null);
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
        }
      });
    } catch (err) {
      setError(errorMessageFromUnknown(err, "request failed"));
      setLiveEvent(null);
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
