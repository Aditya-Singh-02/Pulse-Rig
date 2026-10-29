import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "hardware.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cpus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT UNIQUE,
            socket TEXT,
            ram_type TEXT,
            single_core_score INTEGER,
            multi_core_score INTEGER,
            price_inr INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gpus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT UNIQUE,
            vram_gb INTEGER,
            raster_score INTEGER,
            min_psu_w INTEGER,
            price_inr INTEGER
        )
    """)

    # Seed realistic benchmark data
    cpus = [
        ("Intel Core i5-12400F", "LGA1700", "DDR4", 1720, 12100, 9500),
        ("Intel Core i5-13400F", "LGA1700", "DDR4", 1810, 15800, 15500),
        ("Intel Core i5-13600KF", "LGA1700", "DDR4", 2050, 23500, 22500),
        ("Intel Core i5-14600KF", "LGA1700", "DDR4", 2140, 24800, 24000),
        ("Intel Core i7-14700F", "LGA1700", "DDR4", 2190, 33000, 33500),
        ("AMD Ryzen 5 5600X", "AM4", "DDR4", 1590, 11200, 11500),
        ("AMD Ryzen 7 5700X3D", "AM4", "DDR4", 1950, 14500, 19500),
        ("AMD Ryzen 5 7600X", "AM5", "DDR5", 2020, 15200, 19000),
        ("AMD Ryzen 7 7800X3D", "AM5", "DDR5", 2380, 18900, 36500),
    ]

    gpus = [
        ("NVIDIA GeForce RTX 3060", 12, 100, 550, 24000),
        ("NVIDIA GeForce RTX 4060", 8, 120, 550, 27500),
        ("NVIDIA GeForce RTX 5060", 8, 148, 550, 31000),
        ("AMD Radeon RX 7700 XT", 12, 165, 700, 38500),
        ("NVIDIA GeForce RTX 4070 Super", 12, 198, 650, 56000),
        ("NVIDIA GeForce RTX 5070", 12, 225, 650, 59000),
    ]

    cursor.executemany("INSERT OR IGNORE INTO cpus (model, socket, ram_type, single_core_score, multi_core_score, price_inr) VALUES (?, ?, ?, ?, ?, ?)", cpus)
    cursor.executemany("INSERT OR IGNORE INTO gpus (model, vram_gb, raster_score, min_psu_w, price_inr) VALUES (?, ?, ?, ?, ?)", gpus)

    conn.commit()
    conn.close()


def query_cpu_upgrades(socket: str, ram_type: str, current_model: str) -> list:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Estimate current score
    cursor.execute("SELECT single_core_score FROM cpus WHERE ? LIKE '%' || SUBSTR(model, -6) || '%'", (current_model,))
    row = cursor.fetchone()
    base_score = row[0] if row else 1720  # Default to i5-12400F baseline

    cursor.execute("""
        SELECT model, single_core_score, price_inr
        FROM cpus
        WHERE socket = ? AND ram_type = ? AND single_core_score > ?
    """, (socket, ram_type, int(base_score * 1.15)))

    upgrades = []
    for model, score, price in cursor.fetchall():
        uplift_pct = round(((score - base_score) / base_score) * 100, 1)
        value_index = round((uplift_pct / (price / 1000)), 2)
        upgrades.append({
            "part": model,
            "uplift_percent": f"+{uplift_pct}% Single-Core",
            "price_inr": f"₹{price:,}",
            "value_score": value_index,
            "reason": f"Drop-in {socket} ({ram_type}) upgrade without changing motherboard."
        })

    conn.close()
    return sorted(upgrades, key=lambda x: x["value_score"], reverse=True)[:2]


def query_gpu_upgrades(current_gpu: str) -> list:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    base_score = 148 if "5060" in current_gpu else 120
    cursor.execute("""
        SELECT model, vram_gb, raster_score, price_inr
        FROM gpus
        WHERE raster_score > ?
    """, (int(base_score * 1.25),))

    upgrades = []
    for model, vram, score, price in cursor.fetchall():
        uplift_pct = round(((score - base_score) / base_score) * 100, 1)
        upgrades.append({
            "part": f"{model} ({vram}GB VRAM)",
            "uplift_percent": f"+{uplift_pct}% Raster / +{vram - 8}GB VRAM",
            "price_inr": f"₹{price:,}",
            "value_score": round(uplift_pct / (price / 1000), 2),
            "reason": "Eliminates 1080p Ultra / 1440p rasterization and VRAM bottlenecks."
        })

    conn.close()
    return sorted(upgrades, key=lambda x: x["value_score"], reverse=True)[:2]