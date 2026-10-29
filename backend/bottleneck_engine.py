from hardware_db import query_cpu_upgrades, query_gpu_upgrades


class BottleneckEngine:
    def __init__(self, static_specs: dict):
        self.specs = static_specs

    def analyze(self, processed_telemetry: dict) -> dict:
        s = processed_telemetry["smoothed"]
        zero_cost_fixes = []
        hardware_upgrades = []

        # 1. Always audit static RAM configuration first
        if self.specs["ram_populated_slots"] == 1:
            zero_cost_fixes.append(
                "Single-Channel RAM Detected: Populate 2nd DIMM slot (A2/B2) for Dual-Channel bandwidth (+15-20% 1% Low FPS)."
            )
        if self.specs["ram_type"] == "DDR4" and 0 < self.specs["ram_speed_mhz"] <= 2666:
            zero_cost_fixes.append(
                f"XMP/DOCP Disabled: RAM running at {self.specs['ram_speed_mhz']}MHz JEDEC base speed. Enable XMP Profile 1 in BIOS."
            )

        # 2. Evaluate Live Bottleneck State
        status = "BALANCED / OPTIMAL"
        severity = "healthy"
        explanation = "CPU and GPU workloads are well balanced with no thread starvation or buffer spillover."

        # Check Thermal Throttling first
        if processed_telemetry["gpu_temp_c"] >= 83.0:
            status = "GPU THERMAL THROTTLING"
            severity = "critical"
            explanation = f"GPU temperature reached {processed_telemetry['gpu_temp_c']}°C, forcing clock speed drops."
            zero_cost_fixes.append("Set a steeper GPU fan curve in MSI Afterburner or apply a mild core undervolt.")

        # Check VRAM Spillover
        elif s["vram_percent"] >= 94.0:
            status = "VRAM BUFFER SPILLOVER"
            severity = "critical"
            explanation = f"VRAM usage is at {s['vram_percent']}%. Textures are swapping over PCIe to system RAM, causing frame-time stutters."
            zero_cost_fixes.append("Lower in-game Texture Quality from Ultra to High and disable Ray Tracing.")
            hardware_upgrades = query_gpu_upgrades(self.specs["gpu_model"])

        # Check Single-Thread CPU Bottleneck (Classic Esports / High-Refresh scenario)
        elif s["cpu_max_thread"] >= 90.0 and s["gpu_load"] <= 75.0:
            status = "SINGLE-THREAD CPU BOTTLENECK"
            severity = "warning"
            gap = round(s["cpu_max_thread"] - s["gpu_load"], 1)
            explanation = (
                f"Total CPU usage looks low ({s['cpu_total_load']}%), but primary game thread is pinned at "
                f"{s['cpu_max_thread']}% while GPU waits at {s['gpu_load']}% ({gap}% utilization gap)."
            )
            zero_cost_fixes.extend([
                "Enable NVIDIA Reflex (On + Boost) to synchronize CPU render queue with GPU.",
                "Lower CPU-bound settings: Crowd Density, Player Shadows, and Draw Distance.",
                "Close background browser/Discord hardware acceleration."
            ])
            hardware_upgrades = query_cpu_upgrades(
                self.specs["motherboard_socket"],
                self.specs["ram_type"],
                self.specs["cpu_model"]
            )

        # Check All-Core CPU Bottleneck
        elif s["cpu_total_load"] >= 88.0 and s["gpu_load"] <= 75.0:
            status = "ALL-CORE CPU SATURATION"
            severity = "warning"
            explanation = f"All CPU threads are saturated ({s['cpu_total_load']}%), starving the GPU ({s['gpu_load']}%)."
            zero_cost_fixes.append("Set Windows Power Plan to High Performance and terminate background indexing tasks.")
            hardware_upgrades = query_cpu_upgrades(
                self.specs["motherboard_socket"],
                self.specs["ram_type"],
                self.specs["cpu_model"]
            )

        # Check GPU Bound (Ideal for AAA Gaming, but limits higher FPS)
        elif s["gpu_load"] >= 95.0 and s["cpu_max_thread"] < 85.0:
            status = "GPU RASTERIZATION BOUND"
            severity = "optimal_bound"
            explanation = f"GPU is fully utilized at {s['gpu_load']}% while CPU max thread sits comfortably at {s['cpu_max_thread']}%."
            zero_cost_fixes.append("Enable DLSS / FSR Quality mode or lower Volumetric Fog & Shadow resolution for higher FPS.")
            hardware_upgrades = query_gpu_upgrades(self.specs["gpu_model"])

        if not zero_cost_fixes:
            zero_cost_fixes.append("System configuration (Dual-Channel RAM, thermals, and thread distribution) is optimal.")

        return {
            "status": status,
            "severity": severity,
            "explanation": explanation,
            "zero_cost_fixes": zero_cost_fixes,
            "hardware_upgrades": hardware_upgrades
        }