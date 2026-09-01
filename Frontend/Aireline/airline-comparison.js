/**
 * airline-comparison.js
 * Visualizations with native Chart.js animation configs & interactive handlers.
 */

// Global Chart configuration defaults for smooth transitions

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

Chart.defaults.color = "#94a3b8";
Chart.defaults.font.family = "'Inter', ui-sans-serif, system-ui, sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.animation.duration = 1000;
Chart.defaults.animation.easing = "easeOutQuart";

const GRID_COLOR = "rgba(255, 255, 255, 0.06)";
const TOOLTIP_STYLE = {
  backgroundColor: "#0f172a",
  titleColor: "#e2e8f0",
  bodyColor: "#cbd5e1",
  borderColor: "rgba(148, 163, 184, 0.2)",
  borderWidth: 1,
  padding: 10,
  boxPadding: 4,
  displayColors: true,
};

// Mock airline dataset
const AIRLINES = [
  {
    name: "IndiGo",
    avgFare: 5120,
    change30d: 4.1,
    marketShare: 41.2,
    color: "#60a5fa",
  },
  {
    name: "Air India",
    avgFare: 5860,
    change30d: 7.8,
    marketShare: 24.6,
    color: "#22d3ee",
  },
  {
    name: "SpiceJet",
    avgFare: 4860,
    change30d: -1.3,
    marketShare: 14.9,
    color: "#34d399",
  },
  {
    name: "Vistara",
    avgFare: 6940,
    change30d: 5.5,
    marketShare: 12.1,
    color: "#a78bfa",
  },
  {
    name: "Akasa Air",
    avgFare: 5340,
    change30d: 9.2,
    marketShare: 7.2,
    color: "#fbbf24",
  },
];

// Chart 1: Average fare by airline (bar)
const avgFareCtx = document.getElementById("chart-airline-avg-fare");
if (avgFareCtx) {
  new Chart(avgFareCtx, {
    type: "bar",
    data: {
      labels: AIRLINES.map((a) => a.name),
      datasets: [
        {
          label: "Avg Fare (₹)",
          data: AIRLINES.map((a) => a.avgFare),
          backgroundColor: AIRLINES.map((a) => `${a.color}cc`),
          hoverBackgroundColor: AIRLINES.map((a) => a.color),
          borderRadius: 6,
          borderSkipped: false,
          maxBarThickness: 46,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          ...TOOLTIP_STYLE,
          callbacks: {
            label: (ctx) => `₹${ctx.parsed.y.toLocaleString("en-IN")}`,
          },
        },
      },
      scales: {
        x: { grid: { display: false } },
        y: {
          grid: { color: GRID_COLOR },
          ticks: { callback: (v) => `₹${v.toLocaleString("en-IN")}` },
        },
      },
    },
  });
}

// Render Table with Hover Animation Styles
function renderAirlineRanking() {
  const tbody = document.getElementById("airline-ranking-body");
  if (!tbody) return;

  const sorted = [...AIRLINES].sort((a, b) => a.avgFare - b.avgFare);

  const rows = sorted
    .map((a) => {
      const isUp = a.change30d > 0;
      const changeColor = isUp ? "text-red-400" : "text-emerald-400";
      const arrow = isUp ? "▲" : "▼";

      return `
            <tr class="text-slate-300 hover:bg-white/[0.04] transition-colors duration-150 cursor-pointer">
                <td class="py-2.5 font-medium flex items-center">
                    <span class="airline-dot" style="background-color: ${a.color}"></span>${a.name}
                </td>
                <td class="py-2.5 text-right font-medium">₹${a.avgFare.toLocaleString("en-IN")}</td>
                <td class="py-2.5 text-right ${changeColor} font-medium">${arrow} ${Math.abs(a.change30d).toFixed(1)}%</td>
                <td class="py-2.5 text-right font-medium">${a.marketShare.toFixed(1)}%</td>
            </tr>
        `;
    })
    .join("");

  tbody.innerHTML = rows;
}

renderAirlineRanking();

// Chart 2: Fare by route, grouped by airline
const ROUTES = [
  "DEL → BOM",
  "BLR → DEL",
  "BOM → BLR",
  "DEL → MAA",
  "CCU → DEL",
];
const ROUTE_FARE_MATRIX = {
  IndiGo: [4820, 5340, 4610, 5580, 5250],
  "Air India": [5480, 6120, 5390, 6280, 5910],
  SpiceJet: [4520, 5010, 4380, 5290, 5060],
  Vistara: [6640, 7280, 6410, 7460, 7120],
  "Akasa Air": [5020, 5610, 4890, 5820, 5460],
};

const routeGroupedCtx = document.getElementById("chart-airline-route-grouped");
if (routeGroupedCtx) {
  new Chart(routeGroupedCtx, {
    type: "bar",
    data: {
      labels: ROUTES,
      datasets: AIRLINES.map((a) => ({
        label: a.name,
        data: ROUTE_FARE_MATRIX[a.name],
        backgroundColor: `${a.color}cc`,
        hoverBackgroundColor: a.color,
        borderRadius: 4,
        borderSkipped: false,
        maxBarThickness: 22,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: { boxWidth: 10, boxHeight: 10, padding: 12 },
        },
        tooltip: {
          ...TOOLTIP_STYLE,
          callbacks: {
            label: (ctx) =>
              `${ctx.dataset.label}: ₹${ctx.parsed.y.toLocaleString("en-IN")}`,
          },
        },
      },
      scales: {
        x: { grid: { display: false } },
        y: {
          grid: { color: GRID_COLOR },
          ticks: { callback: (v) => `₹${v.toLocaleString("en-IN")}` },
        },
      },
    },
  });
}

// Chart 3: 30-day price index trend by airline
const indexTrendCtx = document.getElementById("chart-airline-index-trend");
if (indexTrendCtx) {
  const dayLabels = Array.from({ length: 30 }, (_, i) => `D${i + 1}`);

  const datasets = AIRLINES.map((a) => {
    let value = 100;
    const drift = a.change30d / 30;
    const data = dayLabels.map((_, i) => {
      value += drift + Math.sin(i * 0.7 + a.avgFare) * 0.6;
      return Number(value.toFixed(1));
    });
    return {
      label: a.name,
      data,
      borderColor: a.color,
      backgroundColor: a.color,
      pointRadius: 0,
      pointHoverRadius: 5,
      pointHoverBackgroundColor: a.color,
      borderWidth: 2,
      tension: 0.35,
      fill: false,
    };
  });

  new Chart(indexTrendCtx, {
    type: "line",
    data: { labels: dayLabels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: { boxWidth: 10, boxHeight: 10, padding: 12 },
        },
        tooltip: { ...TOOLTIP_STYLE },
      },
      scales: {
        x: { grid: { color: GRID_COLOR }, ticks: { maxTicksLimit: 10 } },
        y: {
          grid: { color: GRID_COLOR },
          title: {
            display: true,
            text: "Index (Base = 100)",
            color: "#64748b",
          },
        },
      },
    },
  });
}

// Refresh button interaction animation
const refreshBtn = document.getElementById("refresh-data-btn");
const refreshIcon = document.getElementById("refresh-icon");

if (refreshBtn && refreshIcon) {
  refreshBtn.addEventListener("click", () => {
    // Trigger CSS rotation on icon click
    refreshIcon.classList.add("rotate-[360deg]");

    setTimeout(() => {
      refreshIcon.classList.remove("rotate-[360deg]");
    }, 700);

    console.log("[airline-comparison] Refreshing data...");
  });
}
