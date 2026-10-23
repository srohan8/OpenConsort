import { useState } from "react";
import { useDeltas } from "../context/DeltaContext";

function DevRow({ entry, isHighlighted, model }) {
  const { moduleColors, lockedSpec } = model;
  const [expanded, setExpanded] = useState(false);
  const moduleName = lockedSpec.modules.find((m) => m.module_number === entry.module_number)?.module_name;

  return (
    <div
      className="dev-row"
      style={{
        "--module-color": moduleColors[entry.module_number],
        outline: isHighlighted ? `2px solid ${moduleColors[entry.module_number]}` : "none",
      }}
    >
      <div className="dev-row-header" onClick={() => setExpanded((e) => !e)}>
        <span className={`dev-row-icon ${entry.status}`}>{entry.status === "done" ? "✓" : "●"}</span>
        <div>
          <div className="dev-row-module-tag">
            <span className="module-badge">MODULE {entry.module_number}</span> {moduleName}
          </div>
          <div className="dev-row-label">{entry.label}</div>
        </div>
        <button className="dev-row-expand" style={{ marginLeft: "auto" }}>
          {expanded ? "Hide logs ▲" : "Show logs ▼"}
        </button>
      </div>
      {expanded && <div className="dev-row-logs appear">{entry.logStub}</div>}
    </div>
  );
}

// A delta thread: a tracked change request, from either the User Flow
// canvas (via its clarifying chat) or a message typed directly here.
// Both sources produce the same delta shape (doc/kickoff-brief-ui-refinements.md
// Part 4's open design question) - shown as one uniform thread type,
// distinguished only by a small source tag.
function DeltaThread({ delta, isHighlighted, model }) {
  const { moduleColors, lockedSpec } = model;
  const [expanded, setExpanded] = useState(false);
  const moduleName = lockedSpec.modules.find((m) => m.module_number === delta.module_number)?.module_name;

  return (
    <div
      className="dev-row delta-thread appear"
      style={{
        "--module-color": moduleColors[delta.module_number] ?? "var(--chrome-accent)",
        outline: isHighlighted ? `2px solid ${moduleColors[delta.module_number]}` : "none",
      }}
    >
      <div className="dev-row-header" onClick={() => setExpanded((e) => !e)}>
        <span className="dev-row-icon in-progress">●</span>
        <div>
          <div className="dev-row-module-tag">
            <span className="module-badge">MODULE {delta.module_number}</span> {moduleName} ·{" "}
            <span className="delta-source-tag">{delta.source === "user_flow_canvas" ? "from User Flow" : "from dev chat"}</span>
          </div>
          <div className="dev-row-label">{delta.summary}</div>
        </div>
        <button className="dev-row-expand" style={{ marginLeft: "auto" }}>
          {expanded ? "Hide details ▲" : "Show details ▼"}
        </button>
      </div>
      {expanded && (
        <div className="dev-row-logs appear delta-qa">
          {delta.clarifying_question && (
            <>
              <div className="qa-line">
                <strong>Q:</strong> {delta.clarifying_question}
              </div>
              <div className="qa-line">
                <strong>A:</strong> {delta.user_answer}
              </div>
            </>
          )}
          {!delta.clarifying_question && <div className="qa-line">{delta.user_answer}</div>}
        </div>
      )}
    </div>
  );
}

function DevChatInput({ selectedModule, lockedSpec }) {
  const { addDelta } = useDeltas();
  const [message, setMessage] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!message.trim()) return;
    addDelta({
      type: "dev_chat_message",
      module_number: selectedModule ?? lockedSpec.modules[0].module_number,
      summary: message.trim(),
      clarifying_question: null,
      user_answer: message.trim(),
      source: "dev_chat",
    });
    setMessage("");
  };

  return (
    <form className="dev-chat-input" onSubmit={handleSubmit}>
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder='Ask for a change (e.g. "add social login")...'
      />
      <button type="submit" className="btn-primary">
        Send
      </button>
    </form>
  );
}

export default function DevelopmentTab({ model, selectedModule }) {
  const { developmentStatus, lockedSpec } = model;
  const { deltas } = useDeltas();

  return (
    <div>
      <h2>Development</h2>
      <p style={{ color: "var(--chrome-text-muted)", marginBottom: 24 }}>
        What's actually being built, in plain language. Expand a row to see the raw logs, or ask
        for a change below.
      </p>
      <div className="dev-rows">
        {developmentStatus.map((entry) => (
          <DevRow
            key={entry.module_number}
            entry={entry}
            isHighlighted={selectedModule === entry.module_number}
            model={model}
          />
        ))}
        {deltas.map((delta) => (
          <DeltaThread key={delta.id} delta={delta} isHighlighted={selectedModule === delta.module_number} model={model} />
        ))}
      </div>
      <DevChatInput selectedModule={selectedModule} lockedSpec={lockedSpec} />
    </div>
  );
}
