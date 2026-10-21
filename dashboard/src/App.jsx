import { useState } from "react";
import { useTickStream } from "./api";
import AgentActivity from "./components/AgentActivity";
import AlertFeed from "./components/AlertFeed";
import IncidentReportModal from "./components/IncidentReportModal";
import KpiHeader from "./components/KpiHeader";
import PermitBoard from "./components/PermitBoard";
import PlantMap from "./components/PlantMap";
import SensorPanel from "./components/SensorPanel";

export default function App() {
  const { payload, connected } = useTickStream();
  const [selectedZone, setSelectedZone] = useState("coke_oven");
  const [reportOpen, setReportOpen] = useState(false);

  if (!payload) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3">
        <h1 className="text-2xl font-black tracking-[0.3em] text-cyan-400">SURAKSHA</h1>
        <p className="animate-pulse text-sm text-slate-500">
          Connecting to plant telemetry…
        </p>
        {import.meta.env.DEV && (
          <p className="text-xs text-slate-600">
            (backend: <span className="font-mono">uvicorn app.main:app --port 8000</span>)
          </p>
        )}
      </div>
    );
  }

  const zone = payload.zones.find((z) => z.id === selectedZone) ?? payload.zones[0];

  return (
    <div className="mx-auto max-w-[1720px] space-y-4 p-4">
      <KpiHeader payload={payload} connected={connected} />

      <main className="grid grid-cols-1 gap-4 xl:grid-cols-5">
        <div className="xl:col-span-3">
          <PlantMap
            zones={payload.zones}
            selectedId={zone.id}
            onSelect={setSelectedZone}
          />
        </div>
        <div className="xl:col-span-2">
          <AlertFeed
            alerts={payload.alerts}
            hasReport={payload.has_report}
            onOpenReport={() => setReportOpen(true)}
          />
        </div>
      </main>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <SensorPanel zone={zone} />
        <PermitBoard permits={payload.permits} zones={payload.zones} />
        <AgentActivity log={payload.agent_log} />
      </section>

      <footer className="pb-2 text-center text-[10px] text-slate-600">
        SURAKSHA · multi-agent industrial safety intelligence · simulated plant demo
      </footer>

      {reportOpen && <IncidentReportModal onClose={() => setReportOpen(false)} />}
    </div>
  );
}
