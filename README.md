#  PulseRig

**Live Hardware Telemetry & Bottleneck Analyzer**

PulseRig is a real-time PC bottleneck diagnostic tool. It polls live hardware sensors, smooths the stream with an EMA filter, classifies the current bottleneck state (CPU, GPU, VRAM, or thermal), and suggests zero-cost fixes plus drop-in hardware upgrades backed by a SQLite benchmark database.

## Architecture

```
PulseRig/
├── backend/
│   ├── main.py                # FastAPI app: REST + WebSocket server, serves the frontend
│   ├── telemetry_agent.py     # HardwareMonitor: polls CPU/GPU/RAM via psutil, pynvml, WMI
│   ├── stream_processor.py    # StreamProcessor: EMA smoothing + transient spike filtering
│   ├── bottleneck_engine.py   # BottleneckEngine: classifies state and recommends fixes
│   └── hardware_db.py         # SQLite schema + seeded benchmark data + upgrade queries
└── frontend/
    ├── index.html             # Dark dashboard UI (Tailwind + Chart.js)
    └── app.js                 # WebSocket client, charts, per-thread grid, simulation controls
```

### Data flow

1. `HardwareMonitor` audits static specs once at startup (CPU model, socket, RAM type/speed/channels) and polls live telemetry continuously.
2. `StreamProcessor` applies an EMA (α=0.2) filter to smooth jitter and flags transient spikes (>25% divergence from EMA).
3. `BottleneckEngine` classifies the workload into one of:
   - `SINGLE-THREAD CPU BOTTLENECK` — esports/high-refresh scenario
   - `ALL-CORE CPU SATURATION` — heavy multithreaded workloads
   - `VRAM BUFFER SPILLOVER` — textures swapping over PCIe
   - `GPU THERMAL THROTTLING` — clock drops from heat
   - `GPU RASTERIZATION BOUND` — GPU-bound, the healthy high-FPS ceiling
4. Each diagnosis carries zero-cost fixes (BIOS/XMP, in-game settings, NVIDIA Reflex, fan curves) and a shortlist of compatible drop-in upgrades from `hardware_db`.

The frontend connects over WebSocket (`/ws/telemetry`) at ~6.6 Hz and renders a live Chart.js stream, a per-core thread grid, and the diagnosis card.

## Features

- **Live hardware telemetry** — CPU load (per-core + max thread), GPU load, VRAM usage/total, GPU temperature, RAM usage
- **Sensor fallbacks** — NVIDIA NVML for GPU metrics, WMI for exact CPU name / RAM speed / dual-channel detection; degrades gracefully when unavailable
- **EMA smoothing** — filters sensor jitter so the diagnosis doesn't chase noise
- **Spike detection** — distinguishes a transient spike from a sustained workload
- **Simulation modes** — synthetic stress profiles for live demos: `cpu_single_thread`, `gpu_bound`, `vram_overflow`
- **SQLite upgrade database** — seeded with benchmark scores and prices; queries return drop-in upgrades matched to your socket/RAM type

## Requirements

- Python 3.10+
- [FastAPI](https://fastapi.tiangolo.com/) and a ASGI server (uvicorn)
- Optional: `pynvml` (NVIDIA GPU metrics), `wmi` + `pythoncom` (Windows WMI), `psutil`

Install dependencies:

```bash
pip install fastapi uvicorn psutil pynvml wmi pythoncom
```

## Running

```bash
cd backend
python main.py
```

The server starts and serves the dashboard at `http://localhost:8000`. The frontend is mounted at `/` automatically.

### Simulation endpoints

```bash
# Switch to a synthetic stress profile (or "live" for real sensors)
POST /api/simulate/cpu_single_thread
POST /api/simulate/gpu_bound
POST /api/simulate/vram_overflow
POST /api/simulate/live
```

## Configuration

All configuration is code-level. To change the WebSocket refresh rate, edit the `asyncio.sleep(0.15)` in `backend/main.py:60`. To change the EMA smoothing factor or buffer size, edit `backend/stream_processor.py:7-8`.

## Data

`backend/hardware.db` is a SQLite database created on first run and seeded with CPU/GPU benchmark data. It is git-ignored — delete it to re-seed from scratch.

## License

MIT