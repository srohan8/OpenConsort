import { lockedSpec, moduleTitles, moduleColors, moduleActionCounts } from "../mockData";
import ModuleHeading from "./ModuleHeading";

export default function ProjectScopeTab({ selectedModule, onSelectModule }) {
  return (
    <div>
      <h2>Project Scope</h2>
      <p style={{ color: "var(--chrome-text-muted)", marginBottom: 24 }}>
        What you're building, grouped into modules.
      </p>
      <div className="module-cards">
        {lockedSpec.modules.map((mod) => {
          const titles = moduleTitles[mod.module_number];
          const counts = moduleActionCounts[mod.module_number] || { done: 0, total: 0 };
          const isSelected = selectedModule === mod.module_number;
          return (
            <button
              key={mod.module_number}
              className={`module-card${isSelected ? " selected" : ""}`}
              style={{ "--module-color": moduleColors[mod.module_number] }}
              onClick={() => onSelectModule(mod.module_number)}
            >
              <ModuleHeading technicalLabel={titles.technicalLabel} plainTitle={titles.plainTitle} />
              <div className="module-card-progress">
                {counts.done}/{counts.total} done
              </div>
              <ul className="module-card-features">
                {mod.features.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </button>
          );
        })}
      </div>
    </div>
  );
}
