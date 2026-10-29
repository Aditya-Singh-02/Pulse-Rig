from collections import deque


class StreamProcessor:
    def __init__(self, buffer_size: int = 60, alpha: float = 0.2):
        self.history = deque(maxlen=buffer_size)
        self.alpha = alpha
        self.ema_state = {
            "cpu_total": None,
            "cpu_max_thread": None,
            "gpu_load": None,
            "vram_percent": None
        }

    def _compute_ema(self, key: str, new_val: float) -> float:
        if self.ema_state[key] is None:
            self.ema_state[key] = new_val
        else:
            self.ema_state[key] = (self.alpha * new_val) + ((1 - self.alpha) * self.ema_state[key])
        return round(self.ema_state[key], 1)

    def process_snapshot(self, raw_telemetry: dict) -> dict:
        ema_cpu_total = self._compute_ema("cpu_total", raw_telemetry["cpu_total_load"])
        ema_cpu_max = self._compute_ema("cpu_max_thread", raw_telemetry["cpu_max_thread"])
        ema_gpu = self._compute_ema("gpu_load", raw_telemetry["gpu_load"])
        ema_vram = self._compute_ema("vram_percent", raw_telemetry["vram_percent"])

        # Detect sudden transient spike (Raw vs EMA divergence > 25%)
        spike_detected = abs(raw_telemetry["cpu_max_thread"] - ema_cpu_max) > 25 or \
                         abs(raw_telemetry["gpu_load"] - ema_gpu) > 25

        processed = {
            **raw_telemetry,
            "smoothed": {
                "cpu_total_load": ema_cpu_total,
                "cpu_max_thread": ema_cpu_max,
                "gpu_load": ema_gpu,
                "vram_percent": ema_vram
            },
            "spike_filtered": spike_detected,
            "is_sustained_workload": (ema_cpu_max > 65.0 or ema_gpu > 65.0)
        }

        self.history.append(processed)
        return processed