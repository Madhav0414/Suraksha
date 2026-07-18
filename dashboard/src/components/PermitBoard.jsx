import Panel from "./Panel";
import { PERMIT_ICONS, PERMIT_LABELS } from "../theme";

export default function PermitBoard({ permits, zones }) {
  const zoneById = Object.fromEntries(zones.map((z) => [z.id, z]));
  const shown = [...permits].reverse(); // newest first

  return (
    <Panel title="Work Permit Board" className="h-full">
      <div className="max-h-[330px] space-y-2.5 overflow-y-auto pr-1">
        {shown.length === 0 && (
          <p className="text-xs text-slate-500">No permits issued in this shift yet.</p>
        )}
        {shown.map((p) => {
          const zone = zoneById[p.zone_id];
          const conflicted =
            p.status === "active" &&
            (zone?.level === "high" || zone?.level === "critical");
          return (
            <div
              key={p.id}
              className={`rounded-lg border bg-[#0a1120] p-3 ${
                conflicted
                  ? "border-rose-500/70 shadow-[0_0_12px_rgba(244,63,94,0.25)]"
                  : "border-slate-800"
              } ${p.status === "closed" ? "opacity-50" : ""}`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-200">
                  {PERMIT_ICONS[p.type]} {PERMIT_LABELS[p.type] ?? p.type}
                </span>
                <span className="flex items-center gap-1.5">
                  {conflicted && (
                    <span className="rounded bg-rose-500/15 px-1.5 py-0.5 text-[10px] font-bold text-rose-400">
                      ⚠ CONFLICT
                    </span>
                  )}
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                      p.status === "active"
                        ? "bg-emerald-500/15 text-emerald-400"
                        : "bg-slate-700/40 text-slate-400"
                    }`}
                  >
                    {p.status.toUpperCase()}
                  </span>
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
                <span>
                  <span className="font-mono text-slate-400">{p.id}</span>
                  {" · "}{zone?.name ?? p.zone_id}
                </span>
                <span className="font-mono">{p.issued_at}</span>
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
