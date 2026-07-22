import { createContext, useContext, useState, useCallback } from "react";

// A "delta request" - the shared shape both the User Flow canvas (via a
// clarifying chat) and a direct dev-chat message produce, per
// doc/kickoff-brief-ui-refinements.md Part 4's open design question: keep
// both paths compatible with one future backend delta-processing mechanism,
// even though neither is wired to a real backend yet (mock/local only).
//
// shape: { id, created_at, type, module_number, summary, clarifying_question,
//          user_answer, source: 'user_flow_canvas' | 'dev_chat' }

const DeltaContext = createContext(null);

export function DeltaProvider({ children }) {
  const [deltas, setDeltas] = useState([]);

  const addDelta = useCallback((delta) => {
    setDeltas((prev) => [
      ...prev,
      {
        id: `delta-${prev.length + 1}-${Math.round(Math.random() * 1e6)}`,
        created_at: new Date().toISOString(),
        ...delta,
      },
    ]);
  }, []);

  return <DeltaContext.Provider value={{ deltas, addDelta }}>{children}</DeltaContext.Provider>;
}

export function useDeltas() {
  const ctx = useContext(DeltaContext);
  if (!ctx) throw new Error("useDeltas must be used within a DeltaProvider");
  return ctx;
}
