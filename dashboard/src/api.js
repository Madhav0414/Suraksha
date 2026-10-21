import { useEffect, useRef, useState } from "react";

// Dev: Vite on :5173 talks to uvicorn on :8000. Built: FastAPI serves the
// dashboard itself, so the API is the same origin.
const API = import.meta.env.DEV ? "http://127.0.0.1:8000" : "";

/** Live tick stream over SSE with automatic reconnect. */
export function useTickStream() {
  const [payload, setPayload] = useState(null);
  const [connected, setConnected] = useState(false);
  const sourceRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    let retryTimer = null;

    const connect = () => {
      if (cancelled) return;
      const es = new EventSource(`${API}/stream`);
      sourceRef.current = es;
      es.addEventListener("tick", (e) => {
        setConnected(true);
        setPayload(JSON.parse(e.data));
      });
      es.onerror = () => {
        setConnected(false);
        es.close();
        retryTimer = setTimeout(connect, 2000);
      };
    };

    connect();
    return () => {
      cancelled = true;
      clearTimeout(retryTimer);
      sourceRef.current?.close();
    };
  }, []);

  return { payload, connected };
}

export const setScenario = (name) =>
  fetch(`${API}/scenario/${name}`, { method: "POST" });

export const setSpeed = (tickMs) =>
  fetch(`${API}/sim/speed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tick_ms: tickMs }),
  });

export const fetchScenarios = () =>
  fetch(`${API}/scenarios`).then((r) => r.json());

export const fetchReport = () =>
  fetch(`${API}/report/latest`).then((r) => {
    if (!r.ok) throw new Error("no report yet");
    return r.json();
  });
