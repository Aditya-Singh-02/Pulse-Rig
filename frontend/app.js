// Initialize Chart.js with optimized continuous streaming animation
const ctx = document.getElementById('telemetryChart').getContext('2d');
const chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: Array(30).fill(''),
        datasets: [
            { 
                label: 'Max Single-Thread CPU %', 
                data: Array(30).fill(0), 
                borderColor: '#f59e0b', 
                backgroundColor: 'rgba(245, 158, 11, 0.15)', 
                tension: 0.4, 
                fill: true,
                pointRadius: 0 
            },
            { 
                label: 'GPU Load %', 
                data: Array(30).fill(0), 
                borderColor: '#06b6d4', 
                backgroundColor: 'rgba(6, 182, 212, 0.15)', 
                tension: 0.4, 
                fill: true,
                pointRadius: 0 
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 200,      // Slightly longer than the 150ms polling rate
            easing: 'linear'    // Creates a continuous, buttery-smooth glide
        },
        parsing: false,   // Bypasses internal object parsing for maximum rendering speed
        normalized: true, // Optimizes memory handling for continuous array shifts
        scales: {
            y: { min: 0, max: 100, grid: { color: '#1f2937' }, ticks: { color: '#9ca3af' } },
            x: { grid: { display: false }, ticks: { display: false } }
        },
        plugins: { legend: { labels: { color: '#d1d5db', font: { size: 11 } } } }
    }
});

async function setSimulation(mode) {
    await fetch(`http://localhost:8000/api/simulate/${mode}`, { method: 'POST' });
}

// WebSocket Connection
const ws = new WebSocket('ws://localhost:8000/ws/telemetry');
const badge = document.getElementById('connection-badge');

ws.onopen = () => {
    badge.textContent = "LIVE 10Hz";
    badge.className = "px-3 py-1 text-xs font-semibold rounded-full bg-emerald-900 text-emerald-300 border border-emerald-700";
};

ws.onclose = () => {
    badge.textContent = "DISCONNECTED";
    badge.className = "px-3 py-1 text-xs font-semibold rounded-full bg-red-900 text-red-300 border border-red-700";
};

let lastGridUpdate = 0;

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    const now = Date.now();
    
    // Update Subtitle Specs (Only once on load or change)
    document.getElementById('system-subtitle').textContent = 
        `${data.specs.cpu_model} | ${data.specs.gpu_model} | RAM: ${data.specs.ram_total_gb}GB (${data.specs.ram_channel_mode}, ${data.specs.ram_speed_mhz}MHz)`;

    // 1. Smooth Chart Render (60Hz+ Glide)
    chart.data.datasets[0].data.shift();
    chart.data.datasets[0].data.push(data.telemetry.smoothed.cpu_max_thread);
    chart.data.datasets[1].data.shift();
    chart.data.datasets[1].data.push(data.telemetry.smoothed.gpu_load);
    chart.update(); // <-- Updates smoothly without the 'none' restriction

    // 2. Throttle DOM Grid & Card updates to every 200ms to keep main thread free for the chart
    if (now - lastGridUpdate > 200) {
        lastGridUpdate = now;

        // Update Per-Thread Grid
        const grid = document.getElementById('thread-grid');
        if (grid.children.length !== data.telemetry.cpu_per_core.length) {
            grid.innerHTML = '';
            data.telemetry.cpu_per_core.forEach((val, idx) => {
                grid.innerHTML += `<div id="thread-${idx}" class="p-2 rounded text-center border border-gray-800">
                    <div class="text-[10px] opacity-75">T${idx}</div>
                    <div class="thread-val text-xs font-bold">${val}%</div>
                </div>`;
            });
        } else {
            data.telemetry.cpu_per_core.forEach((val, idx) => {
                const box = document.getElementById(`thread-${idx}`);
                if (box) {
                    box.className = `p-2 rounded text-center border border-gray-800 ` + 
                        (val > 90 ? 'bg-red-600 text-white' : val > 70 ? 'bg-amber-600 text-white' : 'bg-dark-700 text-gray-300');
                    box.querySelector('.thread-val').textContent = `${val}%`;
                }
            });
        }

        // Update Diagnosis Card
        const diag = data.diagnosis;
        document.getElementById('status-title').textContent = diag.status;
        document.getElementById('status-explanation').textContent = diag.explanation;
        
        const card = document.getElementById('diagnosis-card');
        card.className = `bg-dark-800 border border-gray-800 p-5 rounded-xl shadow-lg border-l-4 ` + 
            (diag.severity === 'critical' ? 'border-l-red-500' : diag.severity === 'warning' ? 'border-l-amber-500' : 'border-l-cyan-500');

        // Update Zero-Cost Fixes
        const fixesList = document.getElementById('fixes-list');
        fixesList.innerHTML = '';
        diag.zero_cost_fixes.forEach(fix => {
            fixesList.innerHTML += `<li>${fix}</li>`;
        });

        // Update SQLite Upgrades
        const upgradesContainer = document.getElementById('upgrades-container');
        upgradesContainer.innerHTML = '';
        if (diag.hardware_upgrades.length === 0) {
            upgradesContainer.innerHTML = `<p class="text-xs text-gray-400 italic">No hardware upgrades required for current workload.</p>`;
        } else {
            diag.hardware_upgrades.forEach(upg => {
                upgradesContainer.innerHTML += `
                    <div class="bg-dark-900 border border-gray-800 p-3 rounded-lg">
                        <div class="text-xs font-bold text-cyan-400">${upg.part}</div>
                        <div class="text-[11px] text-emerald-400 font-semibold">${upg.uplift_percent} (${upg.price_inr})</div>
                        <div class="text-[10px] text-gray-400 mt-1">${upg.reason}</div>
                    </div>`;
            });
        }
    }
};