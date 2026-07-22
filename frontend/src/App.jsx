import { useState } from "react";
import Sidebar from "./components/Sidebar";
import ProjectScopeTab from "./components/ProjectScopeTab";
import UserFlowTab from "./components/UserFlowTab";
import DevelopmentTab from "./components/DevelopmentTab";
import { DeltaProvider } from "./context/DeltaContext";

function App() {
  const [activeTab, setActiveTab] = useState("scope");
  // Shared across all three tabs, keyed by module_number - selecting a
  // module in Project Scope keeps it highlighted in User Flow/Development too.
  const [selectedModule, setSelectedModule] = useState(null);

  return (
    <DeltaProvider>
      <div className="app-shell">
        <Sidebar activeTab={activeTab} onSelectTab={setActiveTab} />
        <main className="content-area">
          {activeTab === "scope" && (
            <ProjectScopeTab selectedModule={selectedModule} onSelectModule={setSelectedModule} />
          )}
          {activeTab === "userflow" && <UserFlowTab selectedModule={selectedModule} />}
          {activeTab === "development" && <DevelopmentTab selectedModule={selectedModule} />}
        </main>
      </div>
    </DeltaProvider>
  );
}

export default App;
