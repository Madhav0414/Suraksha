import { STATUS, levelForScore, levelColor } from "../theme";
import ScenarioControl from "./ScenarioControl";

function Tile({ label, value, sub, color = "#22d3ee", pulse = false }) {
  return (
    <div
      className={`min-w-[128px] rounded-lg border border-slate-800 bg-[#0d1526] px-3.5 py-2 ${pulse ? "animate-kpipulse" : ""}`}
      style={{ borderLeft: `3px solid ${color}` }}
    >
      <div className="text-[10px] font-medium uppercase tracking-wider text-slate-500">
        {label}
      </div>
      <div
        className="font-mono text-xl font-bold tabular-nums leading-6"
        style={{ color }}
      >
        {value}
      </div>
      {sub && <div className="text-[10px] text-slate-500">{sub}</div>}
    </div>
  );
}

export default function KpiHeader({ payload, connected }) {
  const { kpi, sim_time } = payload;
  const riskLevel = levelForScore(kpi.max_risk);
  const lead = kpi.detection_lead_minutes;

  return (
    <header className="flex flex-wrap items-center gap-4">
      <div className="mr-2">
        <h1 className="text-xl font-black tracking-[0.25em] text-cyan-400">
          SURAKSHA
        </h1>
        <p className="text-[11px] tracking-wide text-slate-500">
          Industrial Safety Intelligence
        </p>
      </div>

      <div className="flex flex-1 flex-wrap items-center gap-2.5">
        <Tile
          label="Max Zone Risk"
          value={kpi.max_risk}
          sub={STATUS[riskLevel].label}
          color={levelColor(riskLevel)}
          pulse={kpi.max_risk >= 75}
        />
        <Tile label="Active Permits" value={kpi.active_permits} color="#94a3b8" />
        <Tile label="Workers On Site" value={kpi.workers_on_site} color="#94a3b8" />
        <Tile label="Alerts" value={kpi.alerts_today} color="#eab308" />
        <Tile
          label="Detection Lead"
          value={lead == null ? "—" : `+${lead} min`}
          sub={
            lead == null
              ? "no compound risk yet"
              : kpi.baseline_alarmed
                ? "vs conventional alarm"
                : "conventional alarms still silent"
          }
          color="#22d3ee"
        />
      </div>

      <div className="flex items-center gap-3">
        <ScenarioControl payload={payload} />
        <div className="rounded-lg border border-slate-800 bg-[#0d1526] px-3 py-2 text-right">
          <div className="font-mono text-sm font-semibold text-slate-200">
            {sim_time}
          </div>
          <div className="flex items-center justify-end gap-1.5 text-[10px] text-slate-500">
            <span
              className={`inline-block h-1.5 w-1.5 rounded-full ${connected ? "bg-emerald-400" : "bg-rose-500"}`}
            />
            {connected ? "LIVE" : "RECONNECTING"}
          </div>
        </div>
      </div>
    </header>
  );
}
