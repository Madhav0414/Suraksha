import { Line, LineChart, ResponsiveContainer, Tooltip, YAxis } from "recharts";
import Panel from "./Panel";
import { levelColor } from "../theme";

function pctLevel(pct) {
  return pct >= 100 ? "critical" : pct >= 80 ? "high" : pct >= 60 ? "elevated" : "normal";
}

function SensorCard({ sensor }) {
  const data = sensor.history.map((v, i) => ({ i, v }));
  const badge = levelColor(pctLevel(sensor.pct_critical));
  return (
    <div className="rounded-lg border border-slate-800 bg-[#0a1120] p-3">
      <div className="flex items-baseline justify-between">
        <div>
          <span className="text-sm font-semibold text-slate-200">{sensor.kind}</span>
          <span className="ml-2 font-mono text-[10px] text-slate-500">{sensor.id}</span>
        </div>
        <div className="text-right">
          <span className="font-mono text-sm font-bold tabular-nums text-slate-100">
            {sensor.value}
          </span>
          <span className="ml-1 text-[10px] text-slate-500">{sensor.unit}</span>
        </div>
      </div>
      <div className="mt-1 h-[64px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 2, bottom: 0, left: 2 }}>
            <YAxis hide domain={["auto", "auto"]} />
            <Tooltip
              isAnimationActive={false}
              contentStyle={{
                background: "#0d1526", border: "1px solid #1e293b",
                borderRadius: 8, fontSize: 11, padding: "4px 8px",
              }}
              labelFormatter={() => ""}
              formatter={(v) => [`${v} ${sensor.unit}`, sensor.kind]}
            />
            <Line
              type="monotone" dataKey="v" stroke="#22d3ee" strokeWidth={2}
              dot={false} isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-1.5 flex items-center justify-between">
        <span className="text-[10px] text-slate-500">
          critical at {sensor.critical} {sensor.unit}
        </span>
        <span
          className="rounded px-1.5 py-0.5 font-mono text-[10px] font-bold"
          style={{ color: badge, background: `${badge}22` }}
        >
          {sensor.pct_critical}% of critical
        </span>
      </div>
    </div>
  );
}

export default function SensorPanel({ zone }) {
  return (
    <Panel
      title={`Live Sensors — ${zone?.name ?? ""}`}
      className="h-full"
    >
      <div className="grid max-h-[330px] grid-cols-1 gap-2.5 overflow-y-auto pr-1 xl:grid-cols-2">
        {zone?.sensors.map((s) => <SensorCard key={s.id} sensor={s} />)}
      </div>
    </Panel>
  );
}
