// Shared title hierarchy: a module-number badge + module name above a larger
// plain-English title, per doc/architecture.md's "Module title hierarchy"
// convention and the vintage card treatment from
// doc/kickoff-brief-vintage-cards.md (badge #4, serif title #3).
// technicalLabel is expected in the "Module N · Name" shape produced by
// mockData.js's moduleTitles - parsed here so callers don't need to change.
export default function ModuleHeading({ technicalLabel, plainTitle, as: Tag = "div" }) {
  const match = /Module\s+(\d+)\s*·\s*(.*)/.exec(technicalLabel || "");
  const moduleNumber = match ? match[1] : null;
  const moduleName = match ? match[2] : technicalLabel;

  return (
    <Tag className="module-heading">
      <div className="module-badge-row">
        {moduleNumber && <span className="module-badge">MODULE {moduleNumber}</span>}
        <span className="module-name-label">{moduleName}</span>
      </div>
      <p className="plain-title">{plainTitle}</p>
    </Tag>
  );
}
