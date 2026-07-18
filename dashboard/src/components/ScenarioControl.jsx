import { useEffect, useState } from "react";
import { fetchScenarios, setScenario, setSpeed } from "../api";

const SPEEDS = [
  { label: "1×", tickMs: 1000 },
  { label: "2×", tickMs: 500 },
  { label: "5×", tickMs: 200 },
  { label: "10×", tickMs: 100 },
];

export default function ScenarioControl({ payload }) {
  const [scenarios, setScenarios] = useState([]);
  const [speed, setSpeedState] = useState("1×");

  useEffect(() => {
    fetchScenarios().then(setScenarios).catch(() => {});
  }, []);

  const selectClass =
    "rounded-md border border-slate-700 bg-[#0a1120] px-2 py-1.5 text-xs " +
    "text-slate-200 outline-none focus:border-cyan-500";

  return (
    <div className="flex items-center gap-2 rounded-lg border border-slate-800 bg-[#0d1526] px-3 py-2">
      <label className="text-[10px] uppercase tracking-wider text-slate-500">
        Scenario
      </label>
      <select
        className={selectClass}
        value={payload.scenario}
        onChange={(e) => setScenario(e.target.value)}
      >
        {scenarios.map((s) => (
          <option key={s.name} value={s.name} title={s.description}>
            {s.label}
          </option>
        ))}
      </select>
      <label className="ml-1 text-[10px] uppercase tracking-wider text-slate-500">
        Speed
      </label>
      <select
        className={selectClass}
        value={speed}
        onChange={(e) => {
          const s = SPEEDS.find((x) => x.label === e.target.value);
          setSpeedState(s.label);
          setSpeed(s.tickMs);
        }}
      >
        {SPEEDS.map((s) => (
          <option key={s.label}>{s.label}</option>
        ))}
      </select>
      <button
        onClick={() => setScenario(payload.scenario)}
        className="ml-1 rounded-md border border-slate-700 px-2.5 py-1.5 text-xs text-slate-300 hover:border-cyan-500 hover:text-cyan-300"
        title="Restart current scenario"
      >
        ⟲ Reset
      </button>
    </div>
  );
}
