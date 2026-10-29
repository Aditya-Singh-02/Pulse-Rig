import psutil
import platform
import time

# Attempt to load NVIDIA Management Library
try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False

# Attempt to load Windows Management Instrumentation (WMI)
try:
    import wmi
    import pythoncom
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False


class HardwareMonitor:
    def __init__(self):
        self.gpu_handle = None
        if PYNVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            except Exception as e:
                print(f"[Warning] NVIDIA GPU init failed: {e}")

        # Prime psutil cpu_percent so first call isn't 0.0
        psutil.cpu_percent(percpu=True)

    def get_static_specs(self) -> dict:
        """Runs once at startup to audit physical hardware configuration."""
        specs = {
            "cpu_model": platform.processor(),
            "cpu_physical_cores": psutil.cpu_count(logical=False),
            "cpu_logical_threads": psutil.cpu_count(logical=True),
            "gpu_model": "Generic / Integrated GPU",
            "vram_total_mb": 0,
            "ram_total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 1),
            "ram_speed_mhz": 0,
            "ram_populated_slots": 1,
            "ram_channel_mode": "Unknown",
            "motherboard_socket": "LGA1700",  # Default fallback
            "ram_type": "DDR4"
        }

        # Fetch GPU Name & Total VRAM
        if self.gpu_handle:
            try:
                gpu_name = pynvml.nvmlDeviceGetName(self.gpu_handle)
                specs["gpu_model"] = gpu_name.decode("utf-8") if isinstance(gpu_name, bytes) else gpu_name
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
                specs["vram_total_mb"] = round(mem_info.total / (1024 ** 2))
            except Exception:
                pass

        # Fetch WMI details (CPU Name, RAM Speed, Dual-Channel status)
        if WMI_AVAILABLE:
            try:
                pythoncom.CoInitialize()
                c = wmi.WMI()
                
                # Exact CPU Model Name
                for cpu in c.Win32_Processor():
                    specs["cpu_model"] = cpu.Name.strip()
                    # Infer socket from model string for upgrade matching
                    if any(k in specs["cpu_model"] for k in ["12400", "12600", "13400", "13600", "14400", "14600"]):
                        specs["motherboard_socket"] = "LGA1700"
                    elif any(k in specs["cpu_model"] for k in ["5600", "5700", "5800"]):
                        specs["motherboard_socket"] = "AM4"
                    elif any(k in specs["cpu_model"] for k in ["7600", "7700", "7800"]):
                        specs["motherboard_socket"] = "AM5"

                # RAM Slots and Speed
                mem_modules = c.Win32_PhysicalMemory()
                specs["ram_populated_slots"] = len(mem_modules)
                if mem_modules:
                    speed = getattr(mem_modules[0], "ConfiguredClockSpeed", 0) or getattr(mem_modules[0], "Speed", 0)
                    specs["ram_speed_mhz"] = int(speed) if speed else 3200
                    specs["ram_type"] = "DDR5" if specs["ram_speed_mhz"] >= 4800 else "DDR4"
                    specs["ram_channel_mode"] = "Dual-Channel" if len(mem_modules) >= 2 else "Single-Channel"
            except Exception as e:
                print(f"[Warning] WMI static audit partial failure: {e}")

        return specs

    def get_live_telemetry(self, simulate_mode: str = None) -> dict:
        """Polls instantaneous hardware sensor metrics."""
        if simulate_mode:
            return self._simulate_telemetry(simulate_mode)

        per_core = psutil.cpu_percent(interval=None, percpu=True)
        cpu_total = round(sum(per_core) / len(per_core), 1) if per_core else 0.0
        cpu_max_thread = round(max(per_core), 1) if per_core else 0.0
        ram_info = psutil.virtual_memory()

        gpu_load = 0.0
        vram_used_mb = 0.0
        vram_total_mb = 8192.0
        gpu_temp = 45.0

        if self.gpu_handle:
            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
                gpu_load = float(util.gpu)
                mem = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
                vram_used_mb = round(mem.used / (1024 ** 2), 1)
                vram_total_mb = round(mem.total / (1024 ** 2), 1)
                gpu_temp = float(pynvml.nvmlDeviceGetTemperature(self.gpu_handle, pynvml.NVML_TEMPERATURE_GPU))
            except Exception:
                pass

        return {
            "timestamp": round(time.time(), 2),
            "cpu_total_load": cpu_total,
            "cpu_per_core": per_core,
            "cpu_max_thread": cpu_max_thread,
            "gpu_load": gpu_load,
            "vram_used_mb": vram_used_mb,
            "vram_total_mb": vram_total_mb,
            "vram_percent": round((vram_used_mb / vram_total_mb) * 100, 1) if vram_total_mb else 0.0,
            "gpu_temp_c": gpu_temp,
            "ram_percent": ram_info.percent
        }

    def _simulate_telemetry(self, mode: str) -> dict:
        """Generates realistic synthetic spikes for live presentation demos."""
        import random
        num_threads = psutil.cpu_count(logical=True) or 12

        if mode == "cpu_single_thread":
            # Simulates CS2 / Esports at 1080p: 2 threads maxed out, GPU waiting at 58%
            threads = [round(random.uniform(93, 99), 1) if i < 2 else round(random.uniform(15, 35), 1) for i in range(num_threads)]
            gpu_load = round(random.uniform(52, 64), 1)
            vram_pct = 55.0
            gpu_temp = 61.0
        elif mode == "gpu_bound":
            # Simulates AAA Heavy Graphics: GPU pinned at 99%, CPU comfortable at 50%
            threads = [round(random.uniform(35, 60), 1) for _ in range(num_threads)]
            gpu_load = round(random.uniform(96, 99.5), 1)
            vram_pct = 82.0
            gpu_temp = 74.0
        elif mode == "vram_overflow":
            # Simulates 8GB VRAM buffer spillover
            threads = [round(random.uniform(40, 65), 1) for _ in range(num_threads)]
            gpu_load = round(random.uniform(85, 95), 1)
            vram_pct = round(random.uniform(96, 99.2), 1)
            gpu_temp = 72.0
        else:
            threads = [round(random.uniform(10, 25), 1) for _ in range(num_threads)]
            gpu_load = round(random.uniform(10, 25), 1)
            vram_pct = 30.0
            gpu_temp = 48.0

        return {
            "timestamp": round(time.time(), 2),
            "cpu_total_load": round(sum(threads) / len(threads), 1),
            "cpu_per_core": threads,
            "cpu_max_thread": max(threads),
            "gpu_load": gpu_load,
            "vram_used_mb": round((vram_pct / 100.0) * 8192, 1),
            "vram_total_mb": 8192.0,
            "vram_percent": vram_pct,
            "gpu_temp_c": gpu_temp,
            "ram_percent": 62.5
        }