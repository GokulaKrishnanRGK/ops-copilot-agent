import { FormEvent, UIEvent, useEffect, useMemo, useState } from "react";
import {
  sessionStreamUrl,
  useCreateSessionMutation,
  useDeleteSessionMutation,
  useLazyListSessionsQuery,
  useRenameSessionMutation,
} from "./store/api/sessionApi";
import { useListMessagesQuery } from "./store/api/messageApi";
import { streamChat } from "./lib/sse";
import { ChatEvent, Message, Session, ThemeMode } from "./types";

const THEME_STORAGE_KEY = "opscopilot-theme-mode";
const SESSION_SCROLL_BATCH_SIZE = 5;

type RenderMessage = {
  id: string;
  role: "user" | "assistant" | "event";
  text: string;
};

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12 5v14M5 12h14"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function MoreIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M6 12a1.8 1.8 0 1 0 0 0.01M12 12a1.8 1.8 0 1 0 0 0.01M18 12a1.8 1.8 0 1 0 0 0.01"
        fill="currentColor"
      />
    </svg>
  );
}

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

function sessionLabel(session: Session): string {
  return session.title || session.id.slice(0, 8);
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

function summarizeEvent(event: ChatEvent): string {
  const payload = event.payload;
  if (event.type === "clarifier.clarification_required") {
    const question = payload.question;
    if (typeof question === "string" && question.trim()) {
      return `Clarification needed: ${question}`;
    }
  }
  if (event.type === "error") {
    const message = payload.message;
    if (typeof message === "string" && message.trim()) {
      return `Error: ${message}`;
    }
  }
  if (event.type === "agent_run.failed") {
    const reason = payload.reason;
    if (typeof reason === "string" && reason.trim()) {
      return `Run failed: ${reason}`;
    }
  }
  if (event.type === "agent_run.completed") {
    const summary = payload.summary;
    if (typeof summary === "string" && summary.trim()) {
      return `Run completed: ${summary}`;
    }
  }
  return event.type;
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
  const [streamMessages, setStreamMessages] = useState<RenderMessage[]>([]);
  const [error, setError] = useState<string>("");
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "dark" || stored === "light" || stored === "system") {
      return stored;
    }
    return "system";
  });

  const {
    data: persistedMessages = [],
    error: messagesError,
    refetch: refetchMessages,
  } = useListMessagesQuery(
    { sessionId: activeSessionId },
    {
      skip: !activeSessionId,
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

  const sessionsErrorMessage = sessionsError ? "list sessions failed" : "";
  const messagesErrorMessage = messagesError ? "list messages failed" : "";
  const displayError = error || sessionsErrorMessage || messagesErrorMessage;

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
    const userText = input.trim();
    setInput("");

    const userMessageId = `temp-user-${Date.now()}`;
    const assistantMessageId = `temp-assistant-${Date.now()}`;

    setStreamMessages((prev) => [...prev, { id: userMessageId, role: "user", text: userText }]);
    setLoading(true);

    try {
      await streamChat(sessionStreamUrl(activeSessionId), { message: userText }, (chatEvent) => {
        if (chatEvent.type === "assistant.token.delta") {
          const text = String(chatEvent.payload.text ?? "");
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

        const eventText = summarizeEvent(chatEvent);
        setStreamMessages((prev) => [
          ...prev,
          {
            id: `event-${chatEvent.type}-${chatEvent.timestamp}-${Math.random().toString(36).slice(2)}`,
            role: "event",
            text: eventText,
          },
        ]);

        if (chatEvent.type === "error") {
          const message = chatEvent.payload.message;
          if (typeof message === "string" && message.trim()) {
            setError(message);
          }
        }
      });

      await refetchMessages();
      setStreamMessages((prev) => prev.filter((message) => message.role === "event"));
    } catch (err) {
      setError(errorMessageFromUnknown(err, "request failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <header className="masthead">
        <div className="masthead-copy">
          <h1>Ops Copilot</h1>
          <p>Live operations assistant with streaming execution trace</p>
        </div>
        <label className="theme-switcher">
          Theme
          <select
            value={themeMode}
            onChange={(event) => setThemeMode(event.target.value as ThemeMode)}
          >
            <option value="system">System</option>
            <option value="dark">Dark</option>
            <option value="light">Light</option>
          </select>
        </label>
      </header>
      <main className="layout">
        <aside className="panel sessions">
          <div className="panel-header">
            <h2>Sessions</h2>
            <button
              className="new-chat-button"
              onClick={onCreateSession}
              disabled={isCreatingSession || isRenamingSession || isDeletingSession}
            >
              <PlusIcon />
              <span>New chat</span>
            </button>
          </div>
          <ul onScroll={onSessionListScroll}>
            {sessions.map((session) => {
              const isActive = session.id === activeSessionId;
              const isEditing = session.id === editingSessionId;

              return (
                <li key={session.id} className="session-row">
                  {isEditing ? (
                    <div className="session-edit">
                      <input
                        value={editingTitle}
                        onChange={(event) => setEditingTitle(event.target.value)}
                        disabled={isRenamingSession}
                        placeholder="Session title"
                      />
                      <div className="session-actions">
                        <button
                          onClick={() => void onSaveRename(session.id)}
                          disabled={isRenamingSession}
                        >
                          Save
                        </button>
                        <button
                          className="button-muted"
                          onClick={onCancelRename}
                          disabled={isRenamingSession}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div
                      className={`session-item ${isActive ? "active" : ""} ${openMenuSessionId === session.id ? "menu-open" : ""}`}
                    >
                      <button
                        className="session-select"
                        onClick={() => setActiveSessionId(session.id)}
                        title={sessionLabel(session)}
                      >
                        <span className="session-label">{sessionLabel(session)}</span>
                      </button>
                      <button
                        className="session-more-button"
                        aria-label="Session options"
                        title="More"
                        onClick={(event) => {
                          event.stopPropagation();
                          setOpenMenuSessionId((prev) => (prev === session.id ? "" : session.id));
                        }}
                      >
                        <MoreIcon />
                      </button>
                      {openMenuSessionId === session.id ? (
                        <div
                          className="session-inline-menu"
                          onClick={(event) => event.stopPropagation()}
                        >
                          <button
                            className="context-menu-button"
                            onClick={() => onStartRename(session)}
                          >
                            Rename
                          </button>
                          <button
                            className="context-menu-button"
                            onClick={() => void onDeleteSession(session.id)}
                            disabled={isDeletingSession}
                          >
                            Delete
                          </button>
                        </div>
                      ) : null}
                    </div>
                  )}
                </li>
              );
            })}
            {hasMoreSessions ? (
              <li className="session-load-hint">Scroll for more sessions</li>
            ) : null}
          </ul>
        </aside>
        <section className="panel chat">
          <div className="panel-header">
            <h2>Chat</h2>
            <span>
              {activeSession ? activeSession.title || activeSession.id : "No session selected"}
            </span>
          </div>
          <div className="messages">
            {chatMessages.map((message) => (
              <div key={message.id} className={`message-row ${message.role}`}>
                <p className={`message-text ${message.role}`}>{message.text}</p>
              </div>
            ))}
          </div>
          <form className="composer" onSubmit={onSubmit}>
            <input
              value={input}
              disabled={loading || !activeSessionId}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask about pod status, logs, or events..."
            />
            <button disabled={loading || !activeSessionId}>
              {loading ? "Running..." : "Send"}
            </button>
          </form>
          {displayError ? <div className="error">{displayError}</div> : null}
        </section>
      </main>
    </div>
  );
}
