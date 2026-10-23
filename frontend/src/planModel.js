// Adapts a real Planning result ({locked_spec, user_flow, scenarios, openspec}) to the
// module-grouped shape the Project Scope / User Flow / Development tabs render (the
// same shape as mockData.js), so those layouts work unchanged for real projects.
//
// Modules come from locked_spec.modules. Plans saved before modules existed fall back to
// one module per feature, with screens assigned by word overlap.
import { lockedSpec, moduleTitles, moduleColors, userFlow, developmentStatus, moduleActionCounts } from "./mockData";

export const demoModel = { lockedSpec, moduleTitles, moduleColors, userFlow, developmentStatus, moduleActionCounts };

const PALETTE = ["#8b7fa8", "#6e8fa8", "#7a9b7a", "#b0916a", "#a87f8b", "#7f9ea8"];
const STOP = new Set(["a", "an", "the", "and", "or", "to", "of", "in", "on", "for", "with", "is", "it", "user", "app"]);

function words(text) {
  return new Set(
    (text || "")
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter((w) => w.length > 2 && !STOP.has(w))
  );
}

function overlap(a, b) {
  let n = 0;
  for (const w of a) if (b.has(w)) n += 1;
  return n;
}

function scenarioLine(sc) {
  return `When ${sc.when || "..."}, ${sc.then || "..."}`;
}

// -> [{name, title, features: [name], screens: [id]}]
function planModules(spec, flow, scenarios) {
  if (spec.modules?.length) return spec.modules;

  const featureWords = spec.features.map((f) => words(`${f} ${scenarios[f]?.when || ""} ${scenarios[f]?.then || ""}`));
  const modules = spec.features.map((f) => ({ name: f, title: f, features: [f], screens: [] }));
  for (const screen of flow.screens) {
    const sw = words(`${screen.name} ${screen.purpose}`);
    let best = 0;
    let bestScore = 0;
    featureWords.forEach((fw, i) => {
      const score = overlap(sw, fw);
      if (score > bestScore) {
        best = i;
        bestScore = score;
      }
    });
    modules[best].screens.push(screen.id);
  }
  return modules;
}

export function buildPlanModel(plan) {
  const { locked_spec: spec, user_flow: flow, scenarios = {}, openspec } = plan;
  const planned = planModules(spec, flow, scenarios);

  const moduleOfScreen = {};
  planned.forEach((m, i) =>
    (m.screens || []).forEach((sid) => {
      moduleOfScreen[sid] = i + 1;
    })
  );

  const modules = planned.map((m, i) => ({
    module_number: i + 1,
    module_name: m.name,
    features: m.features.map((f) => (scenarios[f] && (scenarios[f].when || scenarios[f].then) ? scenarioLine(scenarios[f]) : f)),
  }));
  const titles = {};
  const colors = {};
  planned.forEach((m, i) => {
    const n = i + 1;
    titles[n] = { technicalLabel: `Module ${n} · ${m.name}`, plainTitle: m.title || m.name };
    colors[n] = PALETTE[i % PALETTE.length];
  });

  const nameOf = Object.fromEntries(flow.screens.map((s) => [s.id, s.name]));
  const screens = flow.screens.map((s) => {
    const incoming = flow.transitions.find((t) => t.to === s.id);
    return {
      id: s.id,
      module_number: moduleOfScreen[s.id] || 1,
      name: s.name,
      purpose: s.purpose,
      reached_from: incoming
        ? `Reached from ${nameOf[incoming.from] || incoming.from} by: ${incoming.trigger}.`
        : "First screen a user sees.",
      actions: [
        { label: `Show: ${s.purpose}`, done: false },
        ...flow.transitions
          .filter((t) => t.from === s.id)
          .map((t) => ({ label: `${t.trigger} → ${nameOf[t.to] || t.to}`, done: false })),
      ],
    };
  });

  // Progress counts every feature and every screen action; nothing is built yet.
  const counts = {};
  planned.forEach((m, i) => {
    counts[i + 1] = { done: 0, total: m.features.length };
  });
  for (const s of screens) counts[s.module_number].total += s.actions.length;

  return {
    lockedSpec: { product_type: spec.product_type, modules },
    moduleTitles: titles,
    moduleColors: colors,
    userFlow: { screens, transitions: flow.transitions },
    developmentStatus: planned.map((m, i) => ({
      module_number: i + 1,
      status: "planned",
      label: "Planned - not built yet",
      logStub: "No build has run for this module yet.",
    })),
    moduleActionCounts: counts,
    openspec,
  };
}
