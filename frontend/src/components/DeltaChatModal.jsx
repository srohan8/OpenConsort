import { useEffect, useState } from "react";

// Clarifying chat triggered by any User Flow canvas edit (add screen, edit
// node, add/edit connection). No edit is silent - this exchange is what
// actually produces a tracked delta request (doc/kickoff-brief-ui-refinements.md
// Part 4). Feels conversational per Part 5: a brief "thinking" delay before
// the clarifying question appears, rather than popping in instantly.
export default function DeltaChatModal({ pendingEdit, onResolve, onCancel }) {
  const [thinking, setThinking] = useState(true);
  const [answer, setAnswer] = useState("");

  useEffect(() => {
    setThinking(true);
    setAnswer("");
    const t = setTimeout(() => setThinking(false), 500);
    return () => clearTimeout(t);
  }, [pendingEdit]);

  if (!pendingEdit) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!answer.trim()) return;
    onResolve(answer.trim());
  };

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Confirm this change</span>
          <button className="modal-close" onClick={onCancel} aria-label="Cancel">
            ×
          </button>
        </div>
        <div className="chat-thread">
          <div className="chat-bubble user">{pendingEdit.editSummary}</div>
          {thinking ? (
            <div className="chat-bubble bot typing">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          ) : (
            <div className="chat-bubble bot appear">{pendingEdit.clarifyingQuestion}</div>
          )}
        </div>
        {!thinking && (
          <form className="chat-input-row appear" onSubmit={handleSubmit}>
            <input
              autoFocus
              type="text"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Type your answer..."
            />
            <button type="submit" className="btn-primary">
              Confirm change
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
