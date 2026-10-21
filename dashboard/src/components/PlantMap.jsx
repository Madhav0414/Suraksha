import Panel from "./Panel";
import { STATUS, levelColor, levelForScore } from "../theme";

const SHORT_KIND = { pressure: "Press", temp: "Temp" };

/** Live sensor readings, two per row; values tint as they near critical. */
function ZoneReadings({ zone }) {
  const colW = (zone.w - 28) / 2;
  return zone.sensors.map((s, i) => {
    const level = levelForScore(s.pct_critical);
    return (
      <text key={s.id} x={zone.x + 14 + (i % 2) * colW} y={zone.y + 106 + Math.floor(i / 2) * 20}
        fontSize="12" fontFamily="Consolas, monospace">
        <tspan fill="#64748b">{SHORT_KIND[s.kind] ?? s.kind} </tspan>
        <tspan fill={level === "normal" ? "#e2e8f0" : levelColor(level)} fontWeight="700">
          {s.value}
        </tspan>
        <tspan fill="#64748b"> {s.unit}</tspan>
      </text>
    );
  });
}

function ZoneRect({ zone, selected, onSelect }) {
  const color = levelColor(zone.level);
  const hot = zone.level === "high" || zone.level === "critical";
  return (
    <g
      onClick={() => onSelect(zone.id)}
      className="cursor-pointer"
      style={hot ? { filter: `drop-shadow(0 0 10px ${color})` } : undefined}
    >
      <rect
        x={zone.x} y={zone.y} width={zone.w} height={zone.h} rx={10}
        fill={color}
        fillOpacity={0.14}
        stroke={color}
        strokeWidth={selected ? 3 : 1.5}
        className={zone.level === "critical" ? "animate-zonepulse" : ""}
      />
      <text x={zone.x + 14} y={zone.y + 26} fill="#cbd5e1" fontSize="14" fontWeight="600">
        {zone.name}
      </text>
      <text x={zone.x + 14} y={zone.y + 60} fill={color} fontSize="28"
        fontWeight="800" fontFamily="Consolas, monospace">
        {zone.risk}
      </text>
      <text x={zone.x + 14} y={zone.y + 78} fill={color} fontSize="11"
        fontWeight="700" letterSpacing="2">
        {STATUS[zone.level].label}
      </text>
      <ZoneReadings zone={zone} />
      <text x={zone.x + 14} y={zone.y + zone.h - 12} fill="#94a3b8" fontSize="12">
        ⛑ {zone.workers} workers · class {zone.hazard_class}
      </text>
    </g>
  );
}

export default function PlantMap({ zones, selectedId, onSelect }) {
  const selected = zones.find((z) => z.id === selectedId);
  return (
    <Panel
      title="Plant Risk Heatmap"
      right={
        <div className="flex items-center gap-3">
          {Object.entries(STATUS).map(([k, v]) => (
            <span key={k} className="flex items-center gap-1.5 text-[10px] text-slate-400">
              <span className="h-2 w-2 rounded-full" style={{ background: v.color }} />
              {v.label}
            </span>
          ))}
        </div>
      }
    >
      <svg viewBox="0 0 1000 600" className="w-full rounded-lg bg-[#0a1120]">
        {/* subtle grid for the control-room feel */}
        <defs>
          <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
            <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#16233d" strokeWidth="0.6" />
          </pattern>
        </defs>
        <rect width="1000" height="600" fill="url(#grid)" />
        {zones.map((z) => (
          <ZoneRect key={z.id} zone={z} selected={z.id === selectedId} onSelect={onSelect} />
        ))}
      </svg>

      <div className="mt-3 rounded-lg border border-slate-800 bg-[#0a1120] px-4 py-3">
        <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
          Why — {selected?.name} risk factors
        </div>
        {selected?.reasons?.length ? (
          <ul className="mt-1.5 space-y-1">
            {selected.reasons.map((r, i) => (
              <li key={i} className="flex gap-2 text-xs leading-5 text-slate-300">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ background: levelColor(selected.level) }} />
                {r}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-1.5 text-xs text-slate-500">
            No active risk factors — all signals nominal. Click any zone to inspect it.
          </p>
        )}
      </div>
    </Panel>
  );
}
