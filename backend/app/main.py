"""SURAKSHA — Industrial Safety Intelligence Platform. API entrypoint.

Runs the simulation pipeline on a background task and streams every tick to
connected dashboards over SSE. REST endpoints control scenario and speed.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .simulator.scenarios import SCENARIOS
from .state import Pipeline


class Broadcaster:
    def __init__(self):
        self.subscribers: set[asyncio.Queue] = set()

    def publish(self, payload: dict) -> None:
        for q in list(self.subscribers):
            if q.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    q.get_nowait()  # drop oldest — dashboards want latest
            q.put_nowait(payload)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=5)
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.subscribers.discard(q)


class Runtime:
    def __init__(self):
        self.pipeline = Pipeline("normal_day")
        self.tick_ms = 1000
        self.latest: dict = {}
        self.broadcaster = Broadcaster()
        self.lock = asyncio.Lock()

    async def run(self):
        while True:
            async with self.lock:
                self.latest = self.pipeline.step()
                self.broadcaster.publish(self.latest)
            await asyncio.sleep(self.tick_ms / 1000)


runtime = Runtime()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(runtime.run())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="SURAKSHA", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SpeedBody(BaseModel):
    tick_ms: int


@app.get("/health")
def health():
    return {"service": "suraksha", "status": "ok"}


@app.get("/scenarios")
def scenarios():
    return [{"name": s.name, "label": s.label, "description": s.description}
            for s in SCENARIOS.values()]


@app.post("/scenario/{name}")
async def set_scenario(name: str):
    if name not in SCENARIOS:
        raise HTTPException(404, f"unknown scenario '{name}'")
    async with runtime.lock:
        runtime.pipeline = Pipeline(name)
    return {"ok": True, "scenario": name}


@app.post("/sim/speed")
async def set_speed(body: SpeedBody):
    runtime.tick_ms = max(100, min(5000, body.tick_ms))
    return {"ok": True, "tick_ms": runtime.tick_ms}


@app.get("/state")
def state():
    return runtime.latest or {"status": "warming_up"}


@app.get("/report/latest")
def report():
    if not runtime.pipeline.latest_report:
        raise HTTPException(404, "no incident report generated yet")
    return {"markdown": runtime.pipeline.latest_report}


@app.get("/stream")
async def stream():
    q = runtime.broadcaster.subscribe()

    async def gen():
        try:
            if runtime.latest:
                yield {"event": "tick", "data": json.dumps(runtime.latest)}
            while True:
                payload = await q.get()
                yield {"event": "tick", "data": json.dumps(payload)}
        finally:
            runtime.broadcaster.unsubscribe(q)

    return EventSourceResponse(gen())


# Hosted demo: serve the built dashboard from the same origin as the API.
# Mounted last so every API route above takes precedence.
DASHBOARD_DIST = Path(__file__).resolve().parents[2] / "dashboard" / "dist"
if DASHBOARD_DIST.is_dir():
    app.mount("/", StaticFiles(directory=DASHBOARD_DIST, html=True), name="dashboard")
