import { useCallback, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  addEdge,
  useNodesState,
  useEdgesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import ModuleHeading from "./ModuleHeading";
import ScreenNode from "./ScreenNode";
import DeltaChatModal from "./DeltaChatModal";
import { useDeltas } from "../context/DeltaContext";

const NODE_SPACING_X = 190;
const NODE_SPACING_Y = 130;
const NODE_TYPES = { screen: ScreenNode };

function initialNodes(model, highlightModule) {
  const { userFlow, moduleColors } = model;
  return userFlow.screens.map((screen, i) => ({
    id: screen.id,
    type: "screen",
    position: { x: 100 + i * NODE_SPACING_X, y: 60 + (screen.module_number - 1) * NODE_SPACING_Y },
    data: {
      name: screen.name,
      moduleNumber: screen.module_number,
      moduleColor: moduleColors[screen.module_number],
      dimmed: highlightModule != null && screen.module_number !== highlightModule,
      purpose: screen.purpose,
      reached_from: screen.reached_from,
      actions: screen.actions,
    },
  }));
}

function initialEdges(model) {
  const { userFlow } = model;
  return userFlow.transitions.map((t) => ({
    id: `${t.from}-${t.to}`,
    source: t.from,
    target: t.to,
    label: t.trigger,
    animated: false,
  }));
}

function DetailPanel({ screen, moduleTitles }) {
  if (!screen) {
    return (
      <div className="detail-panel">
        <p style={{ color: "var(--chrome-text-muted)" }}>
          Click a screen above to see its details. Double-click a screen to edit it.
        </p>
      </div>
    );
  }
  const titles = moduleTitles[screen.moduleNumber];
  return (
    <div className="detail-panel appear">
      <ModuleHeading technicalLabel={titles?.technicalLabel ?? `Module ${screen.moduleNumber}`} plainTitle={screen.name} />
      <p style={{ margin: "10px 0 4px" }}>{screen.purpose}</p>
      <p className="reached-from">{screen.reached_from}</p>
      <ul className="action-list">
        {(screen.actions || []).map((action) => (
          <li key={action.label} className={action.done ? "done" : "planned"}>
            <span className="icon">{action.done ? "✓" : "○"}</span>
            {action.label}
          </li>
        ))}
      </ul>
    </div>
  );
}

function EditNodePanel({ node, lockedSpec, onSave, onCancel }) {
  const [name, setName] = useState(node.data.name);
  const [moduleNumber, setModuleNumber] = useState(node.data.moduleNumber);

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Edit screen</span>
          <button className="modal-close" onClick={onCancel} aria-label="Cancel">
            ×
          </button>
        </div>
        <label className="field-label">
          Screen title
          <input value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        </label>
        <label className="field-label">
          Module
          <select value={moduleNumber} onChange={(e) => setModuleNumber(Number(e.target.value))}>
            {lockedSpec.modules.map((m) => (
              <option key={m.module_number} value={m.module_number}>
                Module {m.module_number} · {m.module_name}
              </option>
            ))}
          </select>
        </label>
        <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
          <button className="btn-primary" onClick={() => onSave(name, moduleNumber)}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

export default function UserFlowTab({ model, selectedModule }) {
  const { moduleColors, moduleTitles, lockedSpec } = model;
  const { addDelta } = useDeltas();
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes(model, selectedModule));
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges(model));
  const [selectedScreenId, setSelectedScreenId] = useState(null);
  const [editingNode, setEditingNode] = useState(null); // node currently open in EditNodePanel
  const [pendingEdit, setPendingEdit] = useState(null); // {editSummary, clarifyingQuestion, moduleNumber, commit(answer), revert()}

  const selectedScreen = useMemo(() => {
    const n = nodes.find((n) => n.id === selectedScreenId);
    return n ? { ...n.data, id: n.id } : null;
  }, [nodes, selectedScreenId]);

  const onConnect = useCallback(
    (connection) => {
      const newEdgeId = `${connection.source}-${connection.target}`;
      setEdges((eds) => addEdge({ ...connection, id: newEdgeId, animated: true, className: "edge-pulse" }, eds));
      const sourceNode = nodes.find((n) => n.id === connection.source);
      const targetNode = nodes.find((n) => n.id === connection.target);
      setPendingEdit({
        editSummary: `Connected "${sourceNode?.data.name}" → "${targetNode?.data.name}"`,
        clarifyingQuestion: "What should happen when a user does this?",
        moduleNumber: sourceNode?.data.moduleNumber,
        commit: (answer) => {
          addDelta({
            type: "add_connection",
            module_number: sourceNode?.data.moduleNumber,
            summary: `Change requested from User Flow: connected "${sourceNode?.data.name}" → "${targetNode?.data.name}"`,
            clarifying_question: "What should happen when a user does this?",
            user_answer: answer,
            source: "user_flow_canvas",
          });
          setEdges((eds) => eds.map((e) => (e.id === newEdgeId ? { ...e, label: answer, animated: false, className: "" } : e)));
        },
        revert: () => setEdges((eds) => eds.filter((e) => e.id !== newEdgeId)),
      });
    },
    [nodes, setEdges, addDelta]
  );

  const handleAddScreen = () => {
    const newId = `screen-${Date.now()}`;
    const moduleNumber = selectedModule ?? lockedSpec.modules[0].module_number;
    const newNode = {
      id: newId,
      type: "screen",
      position: { x: 100 + Math.random() * 300, y: 60 + Math.random() * 300 },
      data: {
        name: "New screen",
        moduleNumber,
        moduleColor: moduleColors[moduleNumber],
        purpose: "Not yet described.",
        reached_from: "Not yet described.",
        actions: [],
      },
    };
    setNodes((nds) => [...nds, newNode]);
    setPendingEdit({
      editSummary: 'Added a new screen: "New screen"',
      clarifyingQuestion: "What should this screen let a user do?",
      moduleNumber,
      commit: (answer) => {
        addDelta({
          type: "add_screen",
          module_number: moduleNumber,
          summary: `Change requested from User Flow: added "New screen"`,
          clarifying_question: "What should this screen let a user do?",
          user_answer: answer,
          source: "user_flow_canvas",
        });
        setNodes((nds) =>
          nds.map((n) => (n.id === newId ? { ...n, data: { ...n.data, purpose: answer } } : n))
        );
      },
      revert: () => setNodes((nds) => nds.filter((n) => n.id !== newId)),
    });
  };

  const handleEditRequest = (node) => setEditingNode(node);

  const handleSaveEdit = (name, moduleNumber) => {
    const before = { name: editingNode.data.name, moduleNumber: editingNode.data.moduleNumber };
    setNodes((nds) =>
      nds.map((n) =>
        n.id === editingNode.id
          ? { ...n, data: { ...n.data, name, moduleNumber, moduleColor: moduleColors[moduleNumber] } }
          : n
      )
    );
    setEditingNode(null);
    setPendingEdit({
      editSummary: `Edited "${before.name}" → "${name}"${moduleNumber !== before.moduleNumber ? ` (moved to Module ${moduleNumber})` : ""}`,
      clarifyingQuestion: "What's changing about this screen, and why?",
      moduleNumber,
      commit: (answer) => {
        addDelta({
          type: "edit_node",
          module_number: moduleNumber,
          summary: `Change requested from User Flow: edited "${before.name}" → "${name}"`,
          clarifying_question: "What's changing about this screen, and why?",
          user_answer: answer,
          source: "user_flow_canvas",
        });
      },
      revert: () =>
        setNodes((nds) =>
          nds.map((n) =>
            n.id === editingNode.id
              ? { ...n, data: { ...n.data, name: before.name, moduleNumber: before.moduleNumber, moduleColor: moduleColors[before.moduleNumber] } }
              : n
          )
        ),
    });
  };

  const nodesWithHandlers = useMemo(
    () =>
      nodes.map((n) => ({
        ...n,
        selected: n.id === selectedScreenId,
        data: { ...n.data, onEditRequest: () => handleEditRequest(n) },
      })),
    [nodes, selectedScreenId]
  );

  return (
    <div>
      <h2>User Flow</h2>
      <p style={{ color: "var(--chrome-text-muted)", marginBottom: 16 }}>
        The screens your app will have, and how a person moves between them. Drag to reposition,
        double-click a screen to edit it, or draw a new connection between two screens.
      </p>
      <div className="canvas-toolbar">
        <button className="btn-primary" onClick={handleAddScreen}>
          + Add screen
        </button>
      </div>
      <div className="flow-map-wrapper" style={{ height: 420 }}>
        <ReactFlow
          nodes={nodesWithHandlers}
          edges={edges}
          nodeTypes={NODE_TYPES}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={(_, node) => setSelectedScreenId(node.id)}
          fitView
        >
          <Background gap={20} color="#e5e1db" />
          <Controls />
        </ReactFlow>
      </div>
      <DetailPanel screen={selectedScreen} moduleTitles={moduleTitles} />

      {editingNode && (
        <EditNodePanel node={editingNode} lockedSpec={lockedSpec} onSave={handleSaveEdit} onCancel={() => setEditingNode(null)} />
      )}
      {pendingEdit && (
        <DeltaChatModal
          pendingEdit={pendingEdit}
          onResolve={(answer) => {
            pendingEdit.commit(answer);
            setPendingEdit(null);
          }}
          onCancel={() => {
            pendingEdit.revert();
            setPendingEdit(null);
          }}
        />
      )}
    </div>
  );
}
