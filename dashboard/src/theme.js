// Status palette — validated for dark surface with scripts/validate_palette.js
// (dataviz skill). Status colors are never used alone: every use pairs the
// color with the level word and/or numeric score.
export const STATUS = {
  normal:   { color: "#10b981", label: "NORMAL" },
  elevated: { color: "#eab308", label: "ELEVATED" },
  high:     { color: "#f97316", label: "HIGH" },
  critical: { color: "#f43f5e", label: "CRITICAL" },
};

export const levelColor = (level) => (STATUS[level] || STATUS.normal).color;

export const levelForScore = (score) =>
  score >= 75 ? "critical" : score >= 55 ? "high" : score >= 30 ? "elevated" : "normal";

export const AGENT_COLORS = {
  SensorWatch: "#22d3ee",
  PermitIntel: "#eab308",
  Correlator: "#a78bfa",
  Orchestrator: "#f43f5e",
  Compliance: "#10b981",
  Baseline: "#94a3b8",
};

export const PERMIT_ICONS = {
  hot_work: "🔥",
  confined_space: "🕳️",
  maintenance: "🔧",
  electrical: "⚡",
};

export const PERMIT_LABELS = {
  hot_work: "Hot Work",
  confined_space: "Confined Space Entry",
  maintenance: "Maintenance",
  electrical: "Electrical",
};
