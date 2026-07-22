const TABS = [
  { id: "scope", label: "Project Scope", helpText: "What you're building, grouped into modules" },
  { id: "userflow", label: "User Flow", helpText: "The screens your app will have, and how a person moves between them" },
  { id: "development", label: "Development", helpText: "What's being built right now, and how it's going" },
];

export default function Sidebar({ activeTab, onSelectTab }) {
  return (
    <nav className="sidebar">
      <div className="sidebar-title">
        <img src="/logo_text.png" alt="OpenConsort" className="sidebar-logo-text" />
      </div>
      {TABS.map((tab) => (
        <button
          key={tab.id}
          className={`sidebar-tab${activeTab === tab.id ? " active" : ""}`}
          onClick={() => onSelectTab(tab.id)}
        >
          <span className="sidebar-tab-label">{tab.label}</span>
          <span className="sidebar-tab-help">{tab.helpText}</span>
        </button>
      ))}
    </nav>
  );
}
