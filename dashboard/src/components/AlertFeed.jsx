import Panel from "./Panel";
import { levelColor } from "../theme";

const SEVERITY_COLOR = {
  info: "#64748b",
  warning: "#eab308",
  elevated: "#eab308",
  high: "#f97316",
  critical: "#f43f5e",
};

export default function AlertFeed({ alerts, hasReport, onOpenReport }) {
  return (
    <Panel
      title="Alert Feed"
      className="h-full"
      right={
        hasReport && (
          <button
            onClick={onOpenReport}
            className="rounded-md border border-rose-500/60 bg-rose-500/10 px-2.5 py-1 text-[11px] font-semibold text-rose-300 hover:bg-rose-500/20"
          >
            📄 Incident Report
          </button>
        )
      }
    >
      <div className="max-h-[520px] space-y-2 overflow-y-auto pr-1">
        {alerts.length === 0 && (
          <p className="text-xs text-slate-500">
            No alerts. SURAKSHA is watching {`—`} all zones nominal.
          </p>
        )}
        {alerts.map((a, i) => {
          const color = SEVERITY_COLOR[a.severity] ?? "#64748b";
          const isCritical = a.severity === "critical";
          return (
            <div
              key={`${a.ts}-${i}`}
              className={`rounded-lg border p-3 ${
                isCritical
                  ? "border-rose-500/70 bg-rose-500/10"
                  : "border-slate-800 bg-[#0a1120]"
              }`}
              style={{ borderLeft: `3px solid ${color}` }}
            >
              <div className="flex items-start justify-between gap-2">
                <span className={`text-[13px] font-semibold ${isCritical ? "text-rose-200" : "text-slate-200"}`}>
                  {a.title}
                </span>
                <span className="shrink-0 font-mono text-[10px] text-slate-500">{a.ts}</span>
              </div>
              <p className="mt-1 text-xs leading-5 text-slate-400">{a.detail}</p>
              {a.rules?.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {a.rules.map((r) => (
                    <span
                      key={r}
                      className="rounded border border-slate-700 px-1 py-0.5 font-mono text-[9px] text-slate-400"
                    >
                      {r}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
