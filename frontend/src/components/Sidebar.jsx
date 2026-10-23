const PROJECT_TABS = [
  { id: "scope", label: "Project Scope", helpText: "What you're building, grouped into modules" },
  { id: "userflow", label: "User Flow", helpText: "The screens your app will have, and how a person moves between them" },
  { id: "development", label: "Development", helpText: "What's being built right now, and how it's going" },
];

function SidebarTab({ active, label, helpText, onClick }) {
  return (
    <button className={`sidebar-tab${active ? " active" : ""}`} onClick={onClick}>
      <span className="sidebar-tab-label">{label}</span>
      <span className="sidebar-tab-help">{helpText}</span>
    </button>
  );
}

export default function Sidebar({ view, onSelectView, activeProject }) {
  return (
    <nav className="sidebar">
      <div className="sidebar-title">
        <img src="/logo_text.png" alt="OpenConsort" className="sidebar-logo-text" />
      </div>
      <SidebarTab
        active={view === "projects" || view === "new"}
        label="Projects"
        helpText="All your projects, or start a new one"
        onClick={() => onSelectView("projects")}
      />
      {activeProject && (
        <>
          <div className="sidebar-section" title={activeProject.name}>
            {activeProject.name}
          </div>
          {PROJECT_TABS.map((tab) => (
            <SidebarTab
              key={tab.id}
              active={view === tab.id}
              label={tab.label}
              helpText={tab.helpText}
              onClick={() => onSelectView(tab.id)}
            />
          ))}
        </>
      )}
    </nav>
  );
}
