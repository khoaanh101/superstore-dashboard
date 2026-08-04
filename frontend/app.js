"use strict";

/* ============================================
   Storage helpers
   ============================================ */
const STORAGE_KEYS = {
  access: "sd_access_token",
  refresh: "sd_refresh_token",
  email: "sd_user_email",
};

function getTokens() {
  return {
    access: localStorage.getItem(STORAGE_KEYS.access),
    refresh: localStorage.getItem(STORAGE_KEYS.refresh),
    email: localStorage.getItem(STORAGE_KEYS.email),
  };
}

function setTokens({ access, refresh, email }) {
  if (access) localStorage.setItem(STORAGE_KEYS.access, access);
  if (refresh) localStorage.setItem(STORAGE_KEYS.refresh, refresh);
  if (email) localStorage.setItem(STORAGE_KEYS.email, email);
}

function clearTokens() {
  localStorage.removeItem(STORAGE_KEYS.access);
  localStorage.removeItem(STORAGE_KEYS.refresh);
  localStorage.removeItem(STORAGE_KEYS.email);
}

/* ============================================
   API layer
   ============================================ */
class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

/**
 * Perform a fetch against the backend, attaching the access token.
 * On a 401, tries exactly one silent refresh-and-retry before giving up.
 */
async function apiFetch(path, { method = "GET", json, form, retry = true } = {}) {
  const { access } = getTokens();
  const headers = {};
  let body;

  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form !== undefined) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    body = new URLSearchParams(form).toString();
  }

  if (access) headers["Authorization"] = `Bearer ${access}`;

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { method, headers, body });
  } catch (networkErr) {
    throw new ApiError(
      "Cannot connect to server",
      0
    );
  }

  if (response.status === 401 && retry) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      return apiFetch(path, { method, json, form, retry: false });
    }
    forceLogout("Token has expired. Please log in again");
    throw new ApiError("Unauthorized", 401);
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const errBody = await response.json();
      detail = errBody.detail ? JSON.stringify(errBody.detail) : detail;
    } catch (_) {
      /* response had no JSON body */
    }
    throw new ApiError(detail || `HTTP ${response.status}`, response.status);
  }

  if (response.status === 204) return null;
  return response.json();
}

async function tryRefreshToken() {
  // If a refresh is already in flight (e.g. several parallel requests hit
  // 401 at once), share that single promise instead of firing multiple
  // concurrent /auth/refresh calls — the backend rotates refresh tokens,
  // so a second concurrent call would use an already-revoked token and fail.
  if (tryRefreshToken._inFlight) return tryRefreshToken._inFlight;

  const { refresh } = getTokens();
  if (!refresh) return false;

  tryRefreshToken._inFlight = (async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      setTokens({ access: data.access_token, refresh: data.refresh_token });
      return true;
    } catch (_) {
      return false;
    }
  })();

  try {
    return await tryRefreshToken._inFlight;
  } finally {
    tryRefreshToken._inFlight = null;
  }
}

/* ============================================
   View switching
   ============================================ */
function showView(id) {
  for (const el of document.querySelectorAll(".view")) {
    el.hidden = el.id !== id;
  }
}

function forceLogout(message) {
  clearTokens();
  showView("view-login");
  if (message) showToast(message, "error");
}

/* ============================================
   Toast
   ============================================ */
let toastTimer = null;
function showToast(message, kind = "default") {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = "toast" + (kind === "error" ? " toast--error" : "");
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.hidden = true; }, 4000);
}

/* ============================================
   Auth: login / register / logout
   ============================================ */
function setFormError(elId, message) {
  const el = document.getElementById(elId);
  if (!message) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.hidden = false;
  el.textContent = message;
}

async function handleLogin(evt) {
  evt.preventDefault();
  setFormError("login-error", "");
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  const submitBtn = document.getElementById("login-submit");

  submitBtn.disabled = true;
  try {
    const data = await apiFetch("/auth/token", {
      method: "POST",
      form: { username: email, password },
      retry: false,
    });
    setTokens({ access: data.access_token, refresh: data.refresh_token, email });
    await enterDashboard();
  } catch (err) {
    setFormError(
      "login-error",
      err.status === 401 ? "Invalid email/password" : err.message
    );
  } finally {
    submitBtn.disabled = false;
  }
}

async function handleRegister(evt) {
  evt.preventDefault();
  setFormError("register-error", "");
  document.getElementById("register-success").hidden = true;
  const email = document.getElementById("register-email").value.trim();
  const password = document.getElementById("register-password").value;
  const submitBtn = document.getElementById("register-submit");

  submitBtn.disabled = true;
  try {
    await apiFetch("/auth/register", { method: "POST", json: { email, password }, retry: false });
    const successEl = document.getElementById("register-success");
    successEl.hidden = false;
    successEl.textContent = "Registration completed. You can log in now.";
    document.getElementById("register-form").reset();
  } catch (err) {
    setFormError(
      "register-error",
      err.status === 400 ? "This email has already been registered" : err.message
    );
  } finally {
    submitBtn.disabled = false;
  }
}

async function handleLogout() {
  const { refresh } = getTokens();
  if (refresh) {
    try {
      await apiFetch("/auth/logout", { method: "POST", json: { refresh_token: refresh }, retry: false });
    } catch (_) {
      /* best-effort revoke; proceed with local logout regardless */
    }
  }
  clearTokens();
  showView("view-login");
}

/* ============================================
   Formatting helpers
   ============================================ */
const currencyFmt = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});
const numberFmt = new Intl.NumberFormat("en-US");
const decimalFmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });

function formatCurrency(n) { return currencyFmt.format(n); }
function formatNumber(n) { return numberFmt.format(n); }

/* ============================================
   KPI strip
   ============================================ */
// #2 — Single /query/summary request instead of 3 aggregate calls summed client-side.
async function loadKpis() {
  // Show skeleton while loading
  ["kpi-sales", "kpi-profit", "kpi-orders", "kpi-margin"].forEach((id) => {
    const el = document.getElementById(id);
    el.textContent = "\u00a0"; // non-breaking space keeps height
    el.classList.add("skeleton");
  });

  const summary = await apiFetch("/query/summary");

  const totalSales  = summary.total_sales;
  const totalProfit = summary.total_profit;
  const totalOrders = summary.order_count;
  const margin = totalSales > 0 ? (totalProfit / totalSales) * 100 : 0;

  const salesEl = document.getElementById("kpi-sales");
  salesEl.classList.remove("skeleton");
  salesEl.textContent = formatCurrency(totalSales);

  const ordersEl = document.getElementById("kpi-orders");
  ordersEl.classList.remove("skeleton");
  ordersEl.textContent = formatNumber(totalOrders);

  const profitEl = document.getElementById("kpi-profit");
  profitEl.classList.remove("skeleton");
  profitEl.textContent = formatCurrency(totalProfit);
  profitEl.classList.toggle("is-negative", totalProfit < 0);
  profitEl.classList.toggle("is-positive", totalProfit >= 0);

  const marginEl = document.getElementById("kpi-margin");
  marginEl.classList.remove("skeleton");
  marginEl.textContent = `${decimalFmt.format(margin)}%`;
  marginEl.classList.toggle("is-negative", margin < 0);
  marginEl.classList.toggle("is-positive", margin >= 0);
}

/* ============================================
   Charts
   ============================================ */
const chartInstances = {};
const chartFilters = { region: "", category: "", state: "" };

function buildChartQuery(chartType) {
  const params = new URLSearchParams({ chart_type: chartType });
  if (chartFilters.region) params.set("region", chartFilters.region);
  if (chartFilters.category) params.set("category", chartFilters.category);
  if (chartFilters.state) params.set("state", chartFilters.state);
  return params.toString();
}

// #9 — Read theme colors from CSS variables so charts stay in sync with the design system.
function getCssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

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

async function loadCharts() {
  // #9 — Colors sourced from CSS variables, not hardcoded strings.
  const accent     = getCssVar("--accent");      // #D85A30
  const profitPos  = getCssVar("--profit-pos");  // #3B6D11
  const profitNeg  = getCssVar("--profit-neg");  // #A32D2D

  const specs = [
    { type: "sales_by_category",    canvas: "chart-sales-category",    color: accent, xLabel: "Sales (USD)",   yLabel: "Category" },
    { type: "sales_by_region",      canvas: "chart-sales-region",      color: accent, xLabel: "Sales (USD)",   yLabel: "Region" },
    { type: "profit_by_subcategory",canvas: "chart-profit-subcategory",color: null,   xLabel: "Profit (USD)",  yLabel: "Sub-Category" },
    { type: "sales_by_segment",     canvas: "chart-sales-segment",     color: accent, xLabel: "Sales (USD)",   yLabel: "Segment" },
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

/* ============================================
   Manifest table (rows + filters + pagination)
   ============================================ */
const PAGE_SIZE = 20;
const tableState = { offset: 0, category: "", region: "", totalRows: 0 };

// #10 — Load distinct category and region values dynamically from the API.
async function populateFilterOptions() {
  try {
    const [catRes, regRes] = await Promise.all([
      apiFetch("/query/aggregate", {
        method: "POST",
        json: { group_by: "category", metric: "sales", function: "count", limit: 50 },
      }),
      apiFetch("/query/aggregate", {
        method: "POST",
        json: { group_by: "region", metric: "sales", function: "count", limit: 50 },
      }),
    ]);

    const catSelect = document.getElementById("filter-category");
    const regSelect = document.getElementById("filter-region");

    catRes.data
      .map((r) => r.label)
      .sort((a, b) => a.localeCompare(b))
      .forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c;
        opt.textContent = c;
        catSelect.appendChild(opt);
      });

    regRes.data
      .map((r) => r.label)
      .sort((a, b) => a.localeCompare(b))
      .forEach((r) => {
        const opt = document.createElement("option");
        opt.value = r;
        opt.textContent = r;
        regSelect.appendChild(opt);
      });
  } catch (_) { /* non-critical, silently skip */ }
}

function buildRowsQuery() {
  const params = new URLSearchParams();
  if (tableState.category) params.set("category", tableState.category);
  if (tableState.region) params.set("region", tableState.region);
  params.set("limit", String(PAGE_SIZE));
  params.set("offset", String(tableState.offset));
  return params.toString();
}

function renderManifestRows(rows) {
  const tbody = document.getElementById("manifest-body");
  tbody.innerHTML = "";

  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="12" class="empty-row">No rows matched the given filters</td></tr>`;
    return;
  }

  for (const row of rows) {
    const tr = document.createElement("tr");
    const profitClass = row.profit >= 0 ? "profit-pos" : "profit-neg";
    tr.innerHTML = `
      <td>${row.id}</td>
      <td>${escapeHtml(row.ship_mode)}</td>
      <td>${escapeHtml(row.segment)}</td>
      <td>${escapeHtml(row.city)}</td>
      <td>${escapeHtml(row.state)}</td>
      <td>${escapeHtml(row.region)}</td>
      <td>${escapeHtml(row.category)}</td>
      <td>${escapeHtml(row.sub_category)}</td>
      <td class="num">${formatCurrency(row.sales)}</td>
      <td class="num">${formatNumber(row.quantity)}</td>
      <td class="num">${(row.discount * 100).toFixed(0)}%</td>
      <td class="num ${profitClass}">${formatCurrency(row.profit)}</td>
    `;
    tbody.appendChild(tr);
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

async function loadManifestPage() {
  // #7 — Skeleton rows while fetching
  const tbody = document.getElementById("manifest-body");
  tbody.innerHTML = Array.from({ length: 5 }, () =>
    `<tr class="skeleton-row">${Array.from({ length: 12 }, () =>
      `<td><span class="skeleton-cell"></span></td>`).join("")}</tr>`
  ).join("");

  try {
    // #5 — API now returns { total, data } so we can show "X–Y of Z" in the indicator.
    const res = await apiFetch(`/query/rows?${buildRowsQuery()}`);
    const rows  = res.data;
    const total = res.total;
    tableState.totalRows = total;  // store for Last button
    renderManifestRows(rows);

    const from = rows.length === 0 ? 0 : tableState.offset + 1;
    const to   = tableState.offset + rows.length;
    document.getElementById("page-indicator").textContent =
      rows.length === 0 ? "No data" : `Showing ${from}–${to} of ${formatNumber(total)}`;

    const isFirst = tableState.offset === 0;
    const isLast  = rows.length < PAGE_SIZE;
    document.getElementById("btn-first").disabled = isFirst;
    document.getElementById("btn-prev").disabled  = isFirst;
    document.getElementById("btn-next").disabled  = isLast;
    document.getElementById("btn-last").disabled  = isLast;
  } catch (err) {
    if (err.status === 404) {
      renderManifestRows([]);
      document.getElementById("page-indicator").textContent = "Không có dữ liệu";
      ["btn-first", "btn-prev"].forEach((id) => (document.getElementById(id).disabled = tableState.offset === 0));
      ["btn-next",  "btn-last" ].forEach((id) => (document.getElementById(id).disabled = true));
    } else {
      tbody.innerHTML = `<tr><td colspan="12" class="empty-row">Error: ${escapeHtml(err.message)}</td></tr>`;
    }
  }
}

/* ============================================
   Dashboard bootstrap
   ============================================ */
async function populateStateFilter() {
  try {
    const res = await apiFetch("/query/aggregate", {
      method: "POST",
      json: { group_by: "state", metric: "sales", function: "count", limit: 60 },
    });
    const sel = document.getElementById("chart-filter-state");
    const states = res.data.map((r) => r.label).sort((a, b) => a.localeCompare(b));
    for (const s of states) {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s;
      sel.appendChild(opt);
    }
  } catch (_) { /* non-critical, silently skip */ }
}

async function enterDashboard() {
  const { email } = getTokens();
  document.getElementById("topbar-user").textContent = email || "";
  showView("view-dashboard");

  try {
    await Promise.all([
      loadKpis(),
      loadCharts(),
      loadManifestPage(),
      populateStateFilter(),
      populateFilterOptions(),  // #10 — needs auth, so run after login
    ]);
  } catch (err) {
    if (err.status !== 401) showToast(err.message, "error");
  }
}

/* ============================================
   Wire up events
   ============================================ */
function init() {
  // populateFilterOptions is now async + requires auth — called inside enterDashboard() instead.

  document.getElementById("login-form").addEventListener("submit", handleLogin);
  document.getElementById("register-form").addEventListener("submit", handleRegister);

  document.getElementById("show-register").addEventListener("click", () => showView("view-register"));
  document.getElementById("show-login").addEventListener("click", () => showView("view-login"));

  document.getElementById("btn-logout").addEventListener("click", handleLogout);
  document.getElementById("btn-refresh").addEventListener("click", () => {
    loadKpis().catch(() => {});
    loadCharts().catch(() => {});
    loadManifestPage().catch(() => {});
  });

  // Chart filters
  document.getElementById("chart-filter-region").addEventListener("change", (e) => {
    chartFilters.region = e.target.value;
    loadCharts().catch(() => {});
  });
  document.getElementById("chart-filter-category").addEventListener("change", (e) => {
    chartFilters.category = e.target.value;
    loadCharts().catch(() => {});
  });
  document.getElementById("chart-filter-state").addEventListener("change", (e) => {
    chartFilters.state = e.target.value;
    loadCharts().catch(() => {});
  });
  document.getElementById("btn-reset-chart-filters").addEventListener("click", () => {
    chartFilters.region = "";
    chartFilters.category = "";
    chartFilters.state = "";
    document.getElementById("chart-filter-region").value = "";
    document.getElementById("chart-filter-category").value = "";
    document.getElementById("chart-filter-state").value = "";
    loadCharts().catch(() => {});
  });

  // Table filters
  document.getElementById("filter-category").addEventListener("change", (e) => {
    tableState.category = e.target.value;
    tableState.offset = 0;
    loadManifestPage();
  });
  document.getElementById("filter-region").addEventListener("change", (e) => {
    tableState.region = e.target.value;
    tableState.offset = 0;
    loadManifestPage();
  });

  document.getElementById("btn-first").addEventListener("click", () => {
    tableState.offset = 0;
    loadManifestPage();
  });
  document.getElementById("btn-prev").addEventListener("click", () => {
    tableState.offset = Math.max(0, tableState.offset - PAGE_SIZE);
    loadManifestPage();
  });
  document.getElementById("btn-next").addEventListener("click", () => {
    tableState.offset += PAGE_SIZE;
    loadManifestPage();
  });
  document.getElementById("btn-last").addEventListener("click", () => {
    // Calculate the offset of the last page using stored totalRows
    const lastOffset = Math.max(0, Math.floor((tableState.totalRows - 1) / PAGE_SIZE) * PAGE_SIZE);
    tableState.offset = lastOffset;
    loadManifestPage();
  });

  const { access } = getTokens();
  if (access) {
    enterDashboard();
  } else {
    showView("view-login");
  }
}

document.addEventListener("DOMContentLoaded", init);
