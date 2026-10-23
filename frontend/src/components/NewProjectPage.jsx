import { useState } from "react";
import { useProjects } from "../context/ProjectsContext";

const MIN_LENGTH = 10;

export default function NewProjectPage({ onCreated, onCancel }) {
  const { createProject, planProject } = useProjects();
  const [idea, setIdea] = useState("");
  const canSubmit = idea.trim().length >= MIN_LENGTH;

  function handleSubmit(event) {
    event.preventDefault();
    if (!canSubmit) return;
    const project = createProject(idea);
    planProject(project.id, project.idea);
    onCreated(project.id);
  }

  return (
    <form onSubmit={handleSubmit} className="new-project">
      <h2>New project</h2>
      <p style={{ color: "var(--chrome-text-muted)", marginBottom: 20 }}>
        Describe what you want to make in a sentence or two. We'll turn it into a plan you can review
        before anything is built.
      </p>
      <label className="field-label">
        What do you want to build?
        <textarea
          className="idea-input"
          rows={5}
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          placeholder="e.g. A to-do app where I can add tasks, mark them done, and see my progress"
          autoFocus
        />
      </label>
      <div className="form-actions">
        <button type="submit" className="btn-primary" disabled={!canSubmit}>
          Start planning
        </button>
        <button type="button" className="btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
