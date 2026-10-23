// Adapts a real Planning result ({locked_spec, user_flow, scenarios, openspec}) to the
// module-grouped shape the Project Scope / User Flow / Development tabs render (the
// same shape as mockData.js), so those layouts work unchanged for real projects.
//
// The real plan has no modules, so each feature becomes a module and each screen is
// assigned to the feature whose text it overlaps most (first module if none match).
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

export function buildPlanModel(plan) {
  const { locked_spec: spec, user_flow: flow, scenarios = {}, openspec } = plan;

  const featureWords = spec.features.map((f) => words(`${f} ${scenarios[f]?.when || ""} ${scenarios[f]?.then || ""}`));
  const moduleFor = (screen) => {
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
    return best + 1;
  };

  const modules = spec.features.map((f, i) => {
    const sc = scenarios[f];
    return {
      module_number: i + 1,
      module_name: f,
      features: sc && (sc.when || sc.then) ? [`When ${sc.when || "..."}, ${sc.then || "..."}`] : [f],
    };
  });
  const titles = {};
  const colors = {};
  modules.forEach((m) => {
    titles[m.module_number] = { technicalLabel: `Module ${m.module_number} · ${m.module_name}`, plainTitle: m.module_name };
    colors[m.module_number] = PALETTE[(m.module_number - 1) % PALETTE.length];
  });

  const nameOf = Object.fromEntries(flow.screens.map((s) => [s.id, s.name]));
  const screens = flow.screens.map((s) => {
    const incoming = flow.transitions.find((t) => t.to === s.id);
    return {
      id: s.id,
      module_number: moduleFor(s),
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

  const counts = {};
  for (const m of modules) counts[m.module_number] = { done: 0, total: 0 };
  for (const s of screens) counts[s.module_number].total += s.actions.length;

  return {
    lockedSpec: { product_type: spec.product_type, modules },
    moduleTitles: titles,
    moduleColors: colors,
    userFlow: { screens, transitions: flow.transitions },
    developmentStatus: modules.map((m) => ({
      module_number: m.module_number,
      status: "planned",
      label: "Planned - not built yet",
      logStub: "No build has run for this module yet.",
    })),
    moduleActionCounts: counts,
    openspec,
  };
}
