import Panel from "./Panel";
import { AGENT_COLORS } from "../theme";

export default function AgentActivity({ log }) {
  return (
    <Panel title="Agent Activity" className="h-full">
      <div className="max-h-[330px] space-y-1 overflow-y-auto pr-1 font-mono text-[11px] leading-5">
        {log.length === 0 && (
          <p className="text-slate-500">Agents initialising…</p>
        )}
        {log.map((entry, i) => (
          <div key={`${entry.ts}-${i}`} className="flex gap-2">
            <span className="shrink-0 text-slate-600">{entry.ts}</span>
            <span
              className="shrink-0 font-semibold"
              style={{ color: AGENT_COLORS[entry.agent] ?? "#94a3b8" }}
            >
              [{entry.agent}]
            </span>
            <span className="text-slate-400">{entry.line}</span>
          </div>
        ))}
      </div>
    </Panel>
  );
}
