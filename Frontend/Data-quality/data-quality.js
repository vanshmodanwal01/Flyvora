const home = document.getElementById("home");
const route = document.getElementById("route");
const lead = document.getElementById("lead");
const airline = document.getElementById("airline");
const quality = document.getElementById("quality");

home.addEventListener("click", () => {
  window.location.href = "/Frontend/Overview/index.html";
});

route.addEventListener("click", () => {
  window.location.href = "/Frontend/Route_Heatmap+Trends/routeheatmap.html";
});

lead.addEventListener("click", () => {
  window.location.href = "/Frontend/Lead-Time/lead-time.html";
});

airline.addEventListener("click", () => {
  window.location.href = "/Frontend/Aireline/airline-comparison.html";
});

quality.addEventListener("click", () => {
  window.location.href = "/Frontend/Data-quality/data-quality.html";
});

/**
 * data-quality.js
 * Enhanced with Chart.js animations, staggered list entry, count-up metric numbers,
 * and button state interactions.
 */

// Global Chart Defaults
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Inter', ui-sans-serif, system-ui, sans-serif";
Chart.defaults.font.size = 11;

const GRID_COLOR = 'rgba(255, 255, 255, 0.06)';
const TOOLTIP_STYLE = {
    backgroundColor: '#0f172a',
    titleColor: '#e2e8f0',
    bodyColor: '#cbd5e1',
    borderColor: 'rgba(148, 163, 184, 0.2)',
    borderWidth: 1,
    padding: 10,
    boxPadding: 4,
    displayColors: true,
};

// ---------------------------------------------------------------------------
// Animated Metric Number Counter
// ---------------------------------------------------------------------------
function animateValue(element, start, end, duration, formatter = (v) => v.toLocaleString('en-IN')) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        // Easing function: easeOutCubic
        const easedProgress = 1 - Math.pow(1 - progress, 3);
        const current = start + (end - start) * easedProgress;
        element.textContent = formatter(current);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

// ---------------------------------------------------------------------------
// Chart 1: Daily Ingestion Volume (With progressive bar growth)
// ---------------------------------------------------------------------------
let ingestionChart = null;
const dayLabels = Array.from({ length: 30 }, (_, i) => `D${i + 1}`);
const MISSED_RUN_DAYS = [11, 23];

const ingestionVolume = dayLabels.map((_, i) => {
    if (MISSED_RUN_DAYS.includes(i)) return 0;
    const base = 18500;
    const wobble = Math.sin(i * 0.5) * 900 + Math.cos(i * 0.2) * 400;
    return Math.round(base + wobble);
});

function initIngestionChart() {
    const ingestionCtx = document.getElementById('chart-ingestion-volume');
    if (!ingestionCtx) return;

    ingestionChart = new Chart(ingestionCtx, {
        type: 'bar',
        data: {
            labels: dayLabels,
            datasets: [{
                label: 'Records Ingested',
                data: ingestionVolume,
                backgroundColor: ingestionVolume.map((v) =>
                    v === 0 ? 'rgba(248, 113, 113, 0.75)' : 'rgba(96, 165, 250, 0.65)'
                ),
                borderRadius: 4,
                borderSkipped: false,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 1200,
                easing: 'easeOutQuart',
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    ...TOOLTIP_STYLE,
                    callbacks: {
                        label: (ctx) =>
                            ctx.parsed.y === 0
                                ? 'Run failed — 0 records'
                                : `${ctx.parsed.y.toLocaleString('en-IN')} records`,
                    },
                },
            },
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } },
                y: { grid: { color: GRID_COLOR }, ticks: { callback: (v) => v.toLocaleString('en-IN') } },
            },
        },
    });
}

// ---------------------------------------------------------------------------
// Chart 2: Validation Pass Rate (With spring doughnut rotation)
// ---------------------------------------------------------------------------
let validationChart = null;

function initValidationChart() {
    const validationCtx = document.getElementById('chart-validation-rate');
    if (!validationCtx) return;

    validationChart = new Chart(validationCtx, {
        type: 'doughnut',
        data: {
            labels: ['Passed', 'Warned (auto-corrected)', 'Failed'],
            datasets: [{
                data: [98.4, 1.5, 0.1],
                backgroundColor: ['#34d399cc', '#fbbf24cc', '#f87171cc'],
                borderColor: '#0f172a',
                borderWidth: 2,
                hoverOffset: 6
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 1400,
                easing: 'easeOutQuart'
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: { boxWidth: 10, boxHeight: 10, padding: 12 },
                },
                tooltip: {
                    ...TOOLTIP_STYLE,
                    callbacks: { label: (ctx) => `${ctx.label}: ${ctx.parsed}%` },
                },
            },
        },
    });
}

// ---------------------------------------------------------------------------
// Data Source Status List (Staggered Animation)
// ---------------------------------------------------------------------------
const DATA_SOURCES = [
    { name: 'Amadeus API', status: 'Healthy', detail: 'Live fare feed · polled every 15 min', color: '#34d399' },
    { name: 'DGCA Monthly Data', status: 'Healthy', detail: 'Regulatory filing · synced monthly', color: '#34d399' },
    { name: 'Route Metadata Cache', status: 'Degraded', detail: '3 routes missing IATA codes — flagged', color: '#fbbf24' },
    { name: 'Historical Backfill Job', status: 'Idle', detail: 'Last ran 6 days ago · no job scheduled', color: '#94a3b8' },
];

function renderDataSourceStatus() {
    const list = document.getElementById('data-source-status-list');
    if (!list) return;

    list.innerHTML = DATA_SOURCES.map((s, index) => `
        <li class="flex items-center justify-between bg-white/[0.03] border border-white/5 rounded-lg px-3.5 py-2.5 opacity-0 animate-fade-in-up" 
            style="animation-delay: ${index * 80 + 300}ms;">
            <div>
                <p class="text-slate-200 font-medium">${s.name}</p>
                <p class="text-[11px] text-slate-500 mt-0.5">${s.detail}</p>
            </div>
            <span class="status-badge" style="color: ${s.color}; background-color: ${s.color}1a; border: 1px solid ${s.color}40;">
                <span class="status-dot ${s.status === 'Healthy' ? 'status-dot-pulse' : ''}" style="background-color: ${s.color}"></span>${s.status}
            </span>
        </li>
    `).join('');
}

// ---------------------------------------------------------------------------
// Pipeline Run Log Table (Staggered Entry)
// ---------------------------------------------------------------------------
const RUN_LOG = [
    { time: 'Today, 10:00 AM', status: 'Success', records: 18942, duration: '2m 14s' },
    { time: 'Today, 04:00 AM', status: 'Success', records: 18760, duration: '2m 09s' },
    { time: 'Yesterday, 10:00 PM', status: 'Warning', records: 18310, duration: '2m 41s' },
    { time: 'Yesterday, 04:00 PM', status: 'Success', records: 19005, duration: '2m 06s' },
    { time: 'Yesterday, 10:00 AM', status: 'Failed', records: 0, duration: '0m 42s' },
    { time: '2 days ago, 04:00 PM', status: 'Success', records: 18588, duration: '2m 17s' },
];

const STATUS_STYLES = {
    Success: 'text-emerald-400',
    Warning: 'text-amber-400',
    Failed: 'text-red-400',
};

function renderRunLog() {
    const tbody = document.getElementById('pipeline-run-log-body');
    if (!tbody) return;

    tbody.innerHTML = RUN_LOG.map((run, index) => `
        <tr class="text-slate-300 opacity-0 animate-fade-in-up" style="animation-delay: ${index * 60 + 400}ms;">
            <td class="py-2.5">${run.time}</td>
            <td class="py-2.5 font-medium ${STATUS_STYLES[run.status] || 'text-slate-300'}">${run.status}</td>
            <td class="py-2.5 text-right">${run.records.toLocaleString('en-IN')}</td>
            <td class="py-2.5 text-right text-slate-400">${run.duration}</td>
        </tr>
    `).join('');
}

// ---------------------------------------------------------------------------
// Interactive Refresh State with Spinner Animation
// ---------------------------------------------------------------------------
function initRefreshButton() {
    const refreshBtn = document.getElementById('refresh-data-btn');
    if (!refreshBtn) return;

    refreshBtn.addEventListener('click', () => {
        const svg = refreshBtn.querySelector('svg');
        svg.classList.add('animate-spin');
        refreshBtn.disabled = true;
        refreshBtn.classList.add('opacity-75', 'cursor-not-allowed');

        // Re-trigger chart animation update
        if (ingestionChart) ingestionChart.update();
        if (validationChart) validationChart.update();

        setTimeout(() => {
            svg.classList.remove('animate-spin');
            refreshBtn.disabled = false;
            refreshBtn.classList.remove('opacity-75', 'cursor-not-allowed');
        }, 1000);
    });
}

// ---------------------------------------------------------------------------
// Lifecycle Initialization
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    initIngestionChart();
    initValidationChart();
    renderDataSourceStatus();
    renderRunLog();
    initRefreshButton();

    // Trigger number count-up for records ingested metric card
    const recordsMetric = document.querySelector('#metric-records-ingested .metric-value');
    if (recordsMetric) {
        animateValue(recordsMetric, 0, 18942, 1200, (v) => Math.round(v).toLocaleString('en-IN'));
    }
});