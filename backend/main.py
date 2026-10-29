import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from telemetry_agent import HardwareMonitor
from stream_processor import StreamProcessor
from hardware_db import init_db
from bottleneck_engine import BottleneckEngine

app = FastAPI(title="PulseRig Telemetry & Bottleneck Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components on startup
init_db()
monitor = HardwareMonitor()
static_specs = monitor.get_static_specs()
processor = StreamProcessor(buffer_size=60, alpha=0.2)
engine = BottleneckEngine(static_specs)

# State for demo simulation toggle
current_simulation_mode = None


@app.get("/api/specs")
async def get_specs():
    return static_specs


@app.post("/api/simulate/{mode}")
async def set_simulation(mode: str):
    global current_simulation_mode
    current_simulation_mode = None if mode == "live" else mode
    return {"active_mode": current_simulation_mode or "live_hardware"}


@app.websocket("/ws/telemetry")
async def telemetry_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw = monitor.get_live_telemetry(simulate_mode=current_simulation_mode)
            processed = processor.process_snapshot(raw)
            diagnosis = engine.analyze(processed)

            payload = {
                "specs": static_specs,
                "telemetry": processed,
                "diagnosis": diagnosis,
                "mode": current_simulation_mode or "live"
            }
            await websocket.send_json(payload)
            await asyncio.sleep(0.15)  # ~6.6Hz smooth stream
    except WebSocketDisconnect:
        print("Client disconnected from telemetry stream.")


# Mount the frontend directory so FastAPI serves index.html at root "/"
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")