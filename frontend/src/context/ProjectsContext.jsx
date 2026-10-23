import { createContext, useContext, useState, useCallback, useEffect } from "react";

// A project is { id, name, idea, status, created_at }.
//   status 'draft'    - idea captured, Planning has not run yet
//   status 'planning' - waiting on POST /api/plan (orchestrator/server.py)
//   status 'failed'   - planning errored; `error` holds the message, can be retried
//   status 'planned'  - has `plan` {locked_spec, user_flow}; the demo project has none and shows mock data
// Stored in localStorage only; swap for a real backend when the orchestrator is wired up.

const STORAGE_KEY = "openconsort.projects.v1";

const DEMO_PROJECT = {
  id: "demo-todo",
  name: "To-do app (demo)",
  idea: "A to-do list app with sign up, adding and completing tasks, and a progress summary.",
  status: "planned",
  created_at: "2026-01-01T00:00:00.000Z",
};

function load() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
    // a request interrupted by a reload can't still be running
    if (Array.isArray(stored) && stored.length) {
      return stored.map((p) =>
        p.status === "planning" ? { ...p, status: "failed", error: "Planning was interrupted. Try again." } : p
      );
    }
  } catch {
    // storage unavailable or corrupt - fall back to the demo project
  }
  return [DEMO_PROJECT];
}

function nameFromIdea(idea) {
  const text = idea.trim().replace(/\s+/g, " ");
  return text.length > 48 ? `${text.slice(0, 45)}...` : text;
}

const ProjectsContext = createContext(null);

export function ProjectsProvider({ children }) {
  const [projects, setProjects] = useState(load);
  const [activeId, setActiveId] = useState(null);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(projects));
    } catch {
      // ignore: persistence is a convenience
    }
  }, [projects]);

  const createProject = useCallback((idea) => {
    const project = {
      id: `project-${Date.now().toString(36)}`,
      name: nameFromIdea(idea),
      idea: idea.trim(),
      status: "draft",
      created_at: new Date().toISOString(),
    };
    setProjects((prev) => [project, ...prev]);
    setActiveId(project.id);
    return project;
  }, []);

  const updateProject = useCallback((id, changes) => {
    setProjects((prev) => prev.map((p) => (p.id === id ? { ...p, ...changes } : p)));
  }, []);

  const planProject = useCallback(
    async (id, idea) => {
      updateProject(id, { status: "planning", error: null });
      try {
        const res = await fetch("/api/plan", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ idea }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || `Planning failed (HTTP ${res.status})`);
        updateProject(id, { status: "planned", plan: data, error: null });
      } catch (err) {
        const unreachable = err instanceof TypeError;
        updateProject(id, {
          status: "failed",
          error: unreachable ? "Can't reach the planning server. Run `python server.py` in orchestrator/." : err.message,
        });
      }
    },
    [updateProject]
  );

  const deleteProject = useCallback((id) => {
    setProjects((prev) => prev.filter((p) => p.id !== id));
    setActiveId((current) => (current === id ? null : current));
  }, []);

  const activeProject = projects.find((p) => p.id === activeId) || null;

  return (
    <ProjectsContext.Provider
      value={{ projects, activeProject, setActiveId, createProject, planProject, deleteProject }}
    >
      {children}
    </ProjectsContext.Provider>
  );
}

export function useProjects() {
  const ctx = useContext(ProjectsContext);
  if (!ctx) throw new Error("useProjects must be used within a ProjectsProvider");
  return ctx;
}
