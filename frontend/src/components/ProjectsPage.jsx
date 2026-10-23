import { useProjects } from "../context/ProjectsContext";

const STATUS_LABEL = { draft: "Idea saved - not planned yet", planned: "Planned" };

export default function ProjectsPage({ onOpenProject, onNewProject }) {
  const { projects, deleteProject } = useProjects();

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Projects</h2>
          <p style={{ color: "var(--chrome-text-muted)", margin: 0 }}>
            Everything you're building. Pick one to see its plan, or start a new one.
          </p>
        </div>
        <button className="btn-primary" onClick={onNewProject}>
          + New project
        </button>
      </div>
      <div className="module-cards">
        {projects.map((project) => (
          <div key={project.id} className="module-card project-card">
            <button className="project-card-open" onClick={() => onOpenProject(project.id)}>
              <h3 className="plain-title">{project.name}</h3>
              <div className="module-card-progress">{STATUS_LABEL[project.status]}</div>
              <p className="project-card-idea">{project.idea}</p>
            </button>
            <button
              className="project-card-delete"
              aria-label={`Delete ${project.name}`}
              onClick={() => {
                if (window.confirm(`Delete "${project.name}"?`)) deleteProject(project.id);
              }}
            >
              Delete
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
