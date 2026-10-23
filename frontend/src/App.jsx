import { useMemo, useState } from "react";
import Sidebar from "./components/Sidebar";
import ProjectsPage from "./components/ProjectsPage";
import NewProjectPage from "./components/NewProjectPage";
import ProjectScopeTab from "./components/ProjectScopeTab";
import UserFlowTab from "./components/UserFlowTab";
import DevelopmentTab from "./components/DevelopmentTab";
import { buildPlanModel, demoModel } from "./planModel";
import PlanningLoader from "./components/PlanningLoader";
import { DeltaProvider } from "./context/DeltaContext";
import { ProjectsProvider, useProjects } from "./context/ProjectsContext";

function AppShell() {
  const [view, setView] = useState("projects");
  // Shared across all three tabs, keyed by module_number - selecting a
  // module in Project Scope keeps it highlighted in User Flow/Development too.
  const [selectedModule, setSelectedModule] = useState(null);
  const { activeProject, setActiveId, planProject } = useProjects();

  function openProject(id) {
    setActiveId(id);
    setSelectedModule(null);
    setView("scope");
  }

  const isPlanned = activeProject?.status === "planned";
  const model = useMemo(
    () => (activeProject?.plan ? buildPlanModel(activeProject.plan) : demoModel),
    [activeProject?.plan]
  );
  const inProject = ["scope", "userflow", "development"].includes(view) && activeProject;

  return (
    <div className="app-shell">
      <Sidebar view={view} onSelectView={setView} activeProject={activeProject} />
      <main className="content-area">
        {view === "projects" && <ProjectsPage onOpenProject={openProject} onNewProject={() => setView("new")} />}
        {view === "new" && <NewProjectPage onCreated={openProject} onCancel={() => setView("projects")} />}
        {inProject && !isPlanned && (
          <div className="empty-state">
            <h2>{activeProject.name}</h2>
            {activeProject.status === "planning" ? (
              <PlanningLoader />
            ) : (
              <>
                <p>
                  {activeProject.status === "failed"
                    ? "Planning didn't finish."
                    : "Planning hasn't run for this project yet."}{" "}
                  Your idea is saved:
                </p>
                <blockquote>{activeProject.idea}</blockquote>
                {activeProject.error && <p className="error-text">{activeProject.error}</p>}
                <button className="btn-primary" onClick={() => planProject(activeProject.id, activeProject.idea)}>
                  {activeProject.status === "failed" ? "Try again" : "Start planning"}
                </button>
              </>
            )}
          </div>
        )}
        {inProject && isPlanned && view === "scope" && (
          <ProjectScopeTab
            model={model}
            selectedModule={selectedModule}
            onSelectModule={setSelectedModule}
            onRedo={activeProject.plan ? () => planProject(activeProject.id, activeProject.idea) : undefined}
          />
        )}
        {inProject && isPlanned && view === "userflow" && (
          <UserFlowTab key={activeProject.id} model={model} selectedModule={selectedModule} />
        )}
        {inProject && isPlanned && view === "development" && (
          <DevelopmentTab model={model} selectedModule={selectedModule} />
        )}
      </main>
    </div>
  );
}

function App() {
  return (
    <ProjectsProvider>
      <DeltaProvider>
        <AppShell />
      </DeltaProvider>
    </ProjectsProvider>
  );
}

export default App;
