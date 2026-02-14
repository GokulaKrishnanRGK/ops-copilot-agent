import { FormEvent, ReactNode, RefObject, UIEvent } from "react";
import { LogEntry } from "./LogEntry";

export type RenderMessage = {
  id: string;
  role: "user" | "assistant" | "event" | "log";
  text: string;
};

export type LiveEvent = {
  id: string;
  label: string;
  state: "running" | "done";
};

type ChatPanelProps = {
  activeSessionLabel: string;
  summary: ReactNode;
  messages: RenderMessage[];
  liveEvent: LiveEvent | null;
  input: string;
  loading: boolean;
  disabled: boolean;
  error: string;
  messagesContainerRef: RefObject<HTMLDivElement>;
  onMessagesScroll: (event: UIEvent<HTMLDivElement>) => void;
  onInputChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
};

export function ChatPanel({
  activeSessionLabel,
  summary,
  messages,
  liveEvent,
  input,
  loading,
  disabled,
  error,
  messagesContainerRef,
  onMessagesScroll,
  onInputChange,
  onSubmit,
}: ChatPanelProps) {
  return (
    <section className="panel chat">
      <div className="panel-header">
        <h2>Chat</h2>
        <span>{activeSessionLabel}</span>
      </div>
      {summary}
      <div className="messages" ref={messagesContainerRef} onScroll={onMessagesScroll}>
        {messages.map((message) => (
          <div key={message.id} className={`message-row ${message.role}`}>
            {message.role === "log" ? (
              <LogEntry text={message.text} />
            ) : (
              <p className={`message-text ${message.role}`}>{message.text}</p>
            )}
          </div>
        ))}
        {liveEvent ? (
          <div className="live-events">
            <div className="live-event-item">
              {liveEvent.state === "running" ? (
                <span className="event-spinner" aria-hidden="true" />
              ) : null}
              <span>{liveEvent.label}</span>
            </div>
          </div>
        ) : null}
      </div>
      <form className="composer" onSubmit={onSubmit}>
        <input
          value={input}
          disabled={loading || disabled}
          onChange={(event) => onInputChange(event.target.value)}
          placeholder="Ask about pod status, logs, or events..."
        />
        <button disabled={loading || disabled}>{loading ? "Running..." : "Send"}</button>
      </form>
      {error ? <div className="error">{error}</div> : null}
    </section>
  );
}
