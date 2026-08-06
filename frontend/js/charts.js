"use strict";

/* ============================================
   charts.js — Chart rendering, filter state, shared formatters
   Depends on: api.js
   ============================================ */

/* ---- Shared number formatters (used by table.js too) ---- */
const currencyFmt = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});
const numberFmt = new Intl.NumberFormat("en-US");
const decimalFmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });

function formatCurrency(n) { return currencyFmt.format(n); }
function formatNumber(n) { return numberFmt.format(n); }

/* ---- CSS variable helper — keeps chart colors in sync with design system ---- */
function getCssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/* ---- Chart filter state ---- */
const chartFilters = { state: "", city: "" };

// Which filter type is active: "state" or "city"
let chartFilterType = "state";

function buildChartQuery(chartType) {
  const params = new URLSearchParams({ chart_type: chartType });
  if (chartFilterType === "state" && chartFilters.state) params.set("state", chartFilters.state);
  if (chartFilterType === "city"  && chartFilters.city)  params.set("city",  chartFilters.city);
  return params.toString();
}

/* ---- Chart rendering ---- */
const chartInstances = {};

function renderBarChart(canvasId, labels, values, color, { xLabel = "", yLabel = "" } = {}) {
  const ctx = document.getElementById(canvasId).getContext("2d");
  if (chartInstances[canvasId]) chartInstances[canvasId].destroy();

  const titleFont = { family: "Inter", size: 10, weight: "500" };
  const titleColor = "#6B6F76";

  chartInstances[canvasId] = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: color,
        borderRadius: 3,
        maxBarThickness: 22,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          title: {
            display: !!xLabel,
            text: xLabel,
            color: titleColor,
            font: titleFont,
            padding: { top: 6 },
          },
          ticks: { color: "#6B6F76", font: { family: "Inter", size: 10 } },
          grid: { color: "#E5E1D8" },
        },
        y: {
          title: {
            display: !!yLabel,
            text: yLabel,
            color: titleColor,
            font: titleFont,
            padding: { bottom: 6 },
          },
          ticks: { color: "#1F2430", font: { family: "Inter", size: 11 } },
          grid: { display: false },
        },
      },
    },
  });
}

/* ---- Donut chart — Sales by Region (lives in the Total Sales card) ---- */
// A curated palette that pairs well with the design system
const REGION_PALETTE = ["#D85A30", "#3B6D11", "#2D1A6E", "#6B6F76"];

function renderRegionDonut(labels, values) {
  const canvasId = "chart-region-donut";
  const ctx = document.getElementById(canvasId).getContext("2d");
  if (chartInstances[canvasId]) chartInstances[canvasId].destroy();

  const total = values.reduce((s, v) => s + v, 0);

  chartInstances[canvasId] = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: REGION_PALETTE,
        borderWidth: 2,
        borderColor: "#FFFFFF",
        hoverOffset: 4,
      }],
    },
    options: {
      responsive: false,
      cutout: "68%",
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label(ctx) {
              const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
              return ` ${ctx.label}: ${formatCurrency(ctx.parsed)} (${pct}%)`;
            },
          },
        },
      },
    },
  });

  // Build custom legend
  const legendEl = document.getElementById("donut-legend");
  legendEl.innerHTML = "";
  labels.forEach((label, i) => {
    const pct = total > 0 ? ((values[i] / total) * 100).toFixed(1) : "0.0";
    const li = document.createElement("li");
    li.innerHTML = `
      <span class="leg-dot" style="background:${REGION_PALETTE[i % REGION_PALETTE.length]}"></span>
      <span>${label}</span>
      <span class="leg-pct">${pct}%</span>
    `;
    legendEl.appendChild(li);
  });
}

/* Load region donut — NOT filtered (always shows full dataset breakdown) */
async function loadRegionDonut() {
  try {
    const res = await apiFetch("/chart?chart_type=sales_by_region&limit=10");
    const labels = res.data.map((d) => d.label);
    const values = res.data.map((d) => d.value);
    renderRegionDonut(labels, values);
  } catch (_) { /* non-critical */ }
}

async function loadCharts() {
  const accent = getCssVar("--accent");      // #D85A30
  const profitPos = getCssVar("--profit-pos");  // #3B6D11
  const profitNeg = getCssVar("--profit-neg");  // #A32D2D

  const specs = [
    { type: "sales_by_category",  canvas: "chart-sales-category",  color: accent,    xLabel: "Sales (USD)",  yLabel: "Category" },
    { type: "sales_by_ship_mode", canvas: "chart-sales-shipmode",   color: accent,    xLabel: "Sales (USD)",  yLabel: "Ship Mode" },
    { type: "profit_by_subcategory", canvas: "chart-profit-subcategory", color: null, xLabel: "Profit (USD)", yLabel: "Sub-Category" },
    { type: "sales_by_segment",   canvas: "chart-sales-segment",    color: accent,    xLabel: "Sales (USD)",  yLabel: "Segment" },
  ];

  await Promise.all(specs.map(async (spec) => {
    const res = await apiFetch(`/chart?${buildChartQuery(spec.type)}`);
    const labels = res.data.map((d) => d.label);
    const values = res.data.map((d) => d.value);
    const colors = spec.type === "profit_by_subcategory"
      ? values.map((v) => v >= 0 ? profitPos : profitNeg)
      : spec.color;
    renderBarChart(spec.canvas, labels, values, colors, { xLabel: spec.xLabel, yLabel: spec.yLabel });
  }));
}

/* ---- State filter dropdown (populated dynamically from API) ---- */
async function populateStateFilter() {
  try {
    const states = await apiFetch("/query/values/state");
    const sel = document.getElementById("chart-filter-state");
    if (!sel) return;
    sel.innerHTML = '<option value="">All States</option>';
    for (const s of states) {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s;
      sel.appendChild(opt);
    }
  } catch (_) { /* non-critical, silently skip */ }
}

/* ---- City filter dropdown (populated dynamically from API) ---- */
async function populateCityFilter() {
  try {
    const cities = await apiFetch("/query/values/city");
    const sel = document.getElementById("chart-filter-city");
    if (!sel) return;
    sel.innerHTML = '<option value="">All Cities</option>';
    for (const s of cities) {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s;
      sel.appendChild(opt);
    }
  } catch (_) { /* non-critical, silently skip */ }
}

