import { UIEvent } from "react";
import { Session } from "../types";
import { MoreIcon, PlusIcon } from "./icons";

type SessionsPanelProps = {
  sessions: Session[];
  activeSessionId: string;
  editingSessionId: string;
  editingTitle: string;
  openMenuSessionId: string;
  hasMoreSessions: boolean;
  loadingState: {
    creating: boolean;
    renaming: boolean;
    deleting: boolean;
  };
  onCreateSession: () => void;
  onSelectSession: (sessionId: string) => void;
  onStartRename: (session: Session) => void;
  onCancelRename: () => void;
  onSaveRename: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onEditingTitleChange: (value: string) => void;
  onToggleSessionMenu: (sessionId: string) => void;
  onSessionListScroll: (event: UIEvent<HTMLUListElement>) => void;
};

function sessionLabel(session: Session): string {
  return session.title || session.id.slice(0, 8);
}

export function SessionsPanel({
  sessions,
  activeSessionId,
  editingSessionId,
  editingTitle,
  openMenuSessionId,
  hasMoreSessions,
  loadingState,
  onCreateSession,
  onSelectSession,
  onStartRename,
  onCancelRename,
  onSaveRename,
  onDeleteSession,
  onEditingTitleChange,
  onToggleSessionMenu,
  onSessionListScroll,
}: SessionsPanelProps) {
  return (
    <aside className="panel sessions">
      <div className="panel-header">
        <h2>Sessions</h2>
        <button
          className="new-chat-button"
          onClick={onCreateSession}
          disabled={loadingState.creating || loadingState.renaming || loadingState.deleting}
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
                    onChange={(event) => onEditingTitleChange(event.target.value)}
                    disabled={loadingState.renaming}
                    placeholder="Session title"
                  />
                  <div className="session-actions">
                    <button
                      onClick={() => onSaveRename(session.id)}
                      disabled={loadingState.renaming}
                    >
                      Save
                    </button>
                    <button
                      className="button-muted"
                      onClick={onCancelRename}
                      disabled={loadingState.renaming}
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
                    onClick={() => onSelectSession(session.id)}
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
                      onToggleSessionMenu(session.id);
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
                        onClick={() => onDeleteSession(session.id)}
                        disabled={loadingState.deleting}
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
        {hasMoreSessions ? <li className="session-load-hint">Scroll for more sessions</li> : null}
      </ul>
    </aside>
  );
}
