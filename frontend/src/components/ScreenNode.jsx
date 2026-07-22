import { Handle, Position } from "@xyflow/react";

// Custom React Flow node: module tag + plain-English screen name, colored by
// module identity color (kept a fully separate system from the general
// chrome palette, per Part 6's guardrail). Single click selects (shows the
// detail panel); double-click opens the edit-delta flow.
export default function ScreenNode({ data, selected }) {
  return (
    <div
      className={`flow-screen-node${selected ? " selected" : ""}${data.dimmed ? " dimmed" : ""}`}
      style={{ "--module-color": data.moduleColor }}
      onDoubleClick={() => data.onEditRequest?.()}
    >
      <Handle type="target" position={Position.Left} />
      <div className="screen-module-tag">Module {data.moduleNumber}</div>
      <div className="screen-node-name">{data.name}</div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
