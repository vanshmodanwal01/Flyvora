const home = document.getElementById("home");
const route = document.getElementById("route");
const lead = document.getElementById("lead");
const airline = document.getElementById("airline");
const quality = document.getElementById("quality");

home.addEventListener("click", () => {
  window.location.href = "/Overview/index.html";
});

route.addEventListener("click", () => {
  window.location.href = "/Route_Heatmap+Trends/routeheatmap.html";
});

lead.addEventListener("click", () => {
  window.location.href = "/Lead-Time/lead-time.html";
});

airline.addEventListener("click", () => {
  window.location.href = "/Airline/airline-comparison.html";
});

quality.addEventListener("click", () => {
  window.location.href = "/Data-quality/data-quality.html";
});

/**
 * lead-time.js
 * Enhanced with Chart animations, interaction transitions & progressive rendering.
 */

// ---------------------------------------------------------------------------
// Shared Chart.js Defaults
// ---------------------------------------------------------------------------
Chart.defaults.color = '#94a3b8';           // slate-400
Chart.defaults.font.family = "'Inter', ui-sans-serif, system-ui, sans-serif";
Chart.defaults.font.size = 11;

const GRID_COLOR = 'rgba(255, 255, 255, 0.06)';
const TOOLTIP_STYLE = {
    backgroundColor: 'rgba(15, 23, 42, 0.95)',
    titleColor: '#f8fafc',
    bodyColor: '#cbd5e1',
    borderColor: 'rgba(96, 165, 250, 0.2)',
    borderWidth: 1,
    padding: 12,
    boxPadding: 6,
    cornerRadius: 8,
    displayColors: true,
};

const COLORS = {
    blue: '#60a5fa',
    cyan: '#22d3ee',
    amber: '#fbbf24',
    emerald: '#34d399',
    red: '#f87171',
    purple: '#a78bfa',
};

// ---------------------------------------------------------------------------
// Data Generator
// ---------------------------------------------------------------------------
function buildElasticityDataset(basePrice = 4120) {
    const days = [];
    const prices = [];
    for (let d = 45; d >= 1; d--) {
        days.push(d);
        const daysOut = 45 - d;
        const gentle = daysOut * 6;
        const steep = daysOut > 30 ? Math.pow(daysOut - 30, 2.15) * 3.2 : 0;
        const noise = Math.sin(d * 1.3) * 45;
        prices.push(Math.round(basePrice + gentle + steep + noise));
    }
    return { days, prices };
}

const { days: leadTimeDays, prices: leadTimePrices } = buildElasticityDataset(4120);

// ---------------------------------------------------------------------------
// Chart 1: Lead-Time Elasticity Curve (Hero Line Chart)
// ---------------------------------------------------------------------------
let elasticityChart = null;
const elasticityCtx = document.getElementById('chart-lead-time-elasticity');

if (elasticityCtx) {
    elasticityChart = new Chart(elasticityCtx, {
        type: 'line',
        data: {
            labels: leadTimeDays.map((d) => `T-${d}`),
            datasets: [
                {
                    label: 'Avg Fare (₹)',
                    data: leadTimePrices,
                    borderColor: COLORS.blue,
                    backgroundColor: (context) => {
                        const ctx = context.chart.ctx;
                        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
                        gradient.addColorStop(0, 'rgba(96, 165, 250, 0.35)');
                        gradient.addColorStop(1, 'rgba(96, 165, 250, 0.0)');
                        return gradient;
                    },
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: COLORS.blue,
                    pointHoverBorderColor: '#ffffff',
                    pointHoverBorderWidth: 2,
                    borderWidth: 2.5,
                    tension: 0.35,
                    fill: true,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 1800,
                easing: 'easeOutQuart',
            },
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: {
                    ...TOOLTIP_STYLE,
                    callbacks: {
                        label: (ctx) => `Avg Fare: ₹${ctx.parsed.y.toLocaleString('en-IN')}`,
                    },
                },
            },
            scales: {
                x: {
                    reverse: true,
                    grid: { color: GRID_COLOR },
                    ticks: { maxTicksLimit: 12 },
                    title: { display: true, text: 'Days To Departure', color: '#64748b' },
                },
                y: {
                    grid: { color: GRID_COLOR },
                    ticks: { callback: (v) => `₹${v.toLocaleString('en-IN')}` },
                    title: { display: true, text: 'Average Fare', color: '#64748b' },
                },
            },
        },
    });
}

// ---------------------------------------------------------------------------
// Chart 2: Route Elasticity Comparison Chart
// ---------------------------------------------------------------------------
const ROUTE_COMPARISON = [
    { label: 'DEL → BOM', base: 4120, steepness: 3.2, color: COLORS.blue },
    { label: 'BLR → DEL', base: 4550, steepness: 4.6, color: COLORS.cyan },
    { label: 'BOM → BLR', base: 3680, steepness: 2.1, color: COLORS.amber },
];

let routeComparisonChart = null;
const routeComparisonCtx = document.getElementById('chart-route-elasticity-comparison');

if (routeComparisonCtx) {
    const sampleDays = [45, 40, 35, 30, 25, 21, 18, 14, 10, 7, 5, 3, 2, 1];

    const datasets = ROUTE_COMPARISON.map((route) => {
        const data = sampleDays.map((d) => {
            const daysOut = 45 - d;
            const gentle = daysOut * 6;
            const steep = daysOut > 30 ? Math.pow(daysOut - 30, 2.15) * route.steepness : 0;
            return Math.round(route.base + gentle + steep);
        });
        return {
            label: route.label,
            data,
            borderColor: route.color,
            backgroundColor: route.color,
            pointRadius: 3,
            pointHoverRadius: 6,
            borderWidth: 2,
            tension: 0.35,
            fill: false,
        };
    });

    routeComparisonChart = new Chart(routeComparisonCtx, {
        type: 'line',
        data: { labels: sampleDays.map((d) => `T-${d}`), datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 2000,
                easing: 'easeInOutCubic',
            },
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: { boxWidth: 10, boxHeight: 10, padding: 14, usePointStyle: true },
                },
                tooltip: {
                    ...TOOLTIP_STYLE,
                    callbacks: {
                        label: (ctx) => `${ctx.dataset.label}: ₹${ctx.parsed.y.toLocaleString('en-IN')}`,
                    },
                },
            },
            scales: {
                x: { reverse: true, grid: { color: GRID_COLOR } },
                y: {
                    grid: { color: GRID_COLOR },
                    ticks: { callback: (v) => `₹${v.toLocaleString('en-IN')}` },
                },
            },
        },
    });
}

// ---------------------------------------------------------------------------
// Checkpoint Breakdown Table with Staggered Entrance Animation
// ---------------------------------------------------------------------------
const CHECKPOINTS = [45, 30, 21, 14, 7, 3, 1];

function renderCheckpointBreakdown() {
    const tbody = document.getElementById('checkpoint-breakdown-body');
    if (!tbody) return;

    const basePrice = leadTimePrices[leadTimeDays.indexOf(45)];
    const rows = CHECKPOINTS.map((d, idx) => {
        const price = leadTimePrices[leadTimeDays.indexOf(d)];
        const pctChange = ((price - basePrice) / basePrice) * 100;
        const isUp = pctChange > 0;
        const changeColor = isUp ? 'text-red-400 font-semibold' : 'text-emerald-400 font-semibold';
        const arrow = isUp ? '▲' : '▼';

        return `
            <tr class="checkpoint-row text-slate-300 hover:bg-white/[0.04] transition-colors duration-200" style="animation-delay: ${idx * 60}ms;">
                <td class="py-2.5 font-medium">T-${d} ${d === 1 ? '<span class="text-xs text-slate-500 font-normal">(Departure Eve)</span>' : ''}</td>
                <td class="py-2.5 text-right font-mono">₹${price.toLocaleString('en-IN')}</td>
                <td class="py-2.5 text-right ${changeColor}">${arrow} ${Math.abs(pctChange).toFixed(1)}%</td>
            </tr>
        `;
    }).join('');

    tbody.innerHTML = rows;
}

renderCheckpointBreakdown();

// ---------------------------------------------------------------------------
// Refresh Button Trigger with Animation State
// ---------------------------------------------------------------------------
const refreshBtn = document.getElementById('refresh-data-btn');
const refreshIcon = document.getElementById('refresh-icon');

if (refreshBtn && refreshIcon) {
    refreshBtn.addEventListener('click', () => {
        // Trigger spin state
        refreshIcon.classList.add('rotate-180');
        
        // Re-render charts with animation reset
        if (elasticityChart) elasticityChart.update();
        if (routeComparisonChart) routeComparisonChart.update();
        renderCheckpointBreakdown();

        setTimeout(() => {
            refreshIcon.classList.remove('rotate-180');
        }, 500);
    });
}