"use strict";

/* ============================================
   app.js — Bootstrap: KPI strip, enterDashboard, init()
   Depends on: storage.js, api.js, ui.js, auth.js, charts.js, table.js
   ============================================ */

/* ---- KPI strip ---- */
async function loadKpis() {
  // Show skeleton while loading
  ["kpi-sales", "kpi-profit", "kpi-orders", "kpi-margin"].forEach((id) => {
    const el = document.getElementById(id);
    el.textContent = "\u00a0"; // non-breaking space keeps card height stable
    el.classList.add("skeleton");
  });

  const summary = await apiFetch("/query/summary");
  const totalSales = summary.total_sales;
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
   Chart filter helpers — module-level so enterDashboard can call syncFilterDropdown
   ============================================ */

/** Rebuild the visible dropdown from the hidden source select */
function syncFilterDropdown(type) {
  const valueSelect = document.getElementById("chart-filter-value");
  const source      = document.getElementById(type === "state" ? "chart-filter-state" : "chart-filter-city");
  const placeholder = type === "state" ? "All States" : "All Cities";
  const prev        = chartFilters[type];

  valueSelect.innerHTML = `<option value="">${placeholder}</option>`;
  for (const opt of source.options) {
    if (!opt.value) continue;
    const o = document.createElement("option");
    o.value = opt.value;
    o.textContent = opt.textContent;
    if (opt.value === prev) o.selected = true;
    valueSelect.appendChild(o);
  }
  valueSelect.value = prev || "";
}

/** Switch active toggle button and swap dropdown options */
function activateFilterType(type) {
  chartFilterType = type;
  document.getElementById("toggle-filter-state").classList.toggle("is-active", type === "state");
  document.getElementById("toggle-filter-city").classList.toggle("is-active",  type === "city");
  syncFilterDropdown(type);
}

/* ---- Dashboard bootstrap ---- */
async function enterDashboard() {
  const { email, role } = getTokens();
  document.getElementById("topbar-user").textContent = email || "";

  // Role badge
  const badge = document.getElementById("role-badge");
  badge.textContent = role === "admin" ? "Admin" : "Viewer";
  badge.className = `role-badge role-${role === "admin" ? "admin" : "viewer"}`;
  badge.hidden = false;

  // Show / hide admin-only UI elements
  const isAdmin = role === "admin";
  document.getElementById("btn-add-order").hidden = !isAdmin;
  document.getElementById("col-actions").hidden = !isAdmin;

  showView("view-dashboard");

  try {
    await Promise.all([
      loadKpis(),
      loadCharts(),
      loadRegionDonut(),
      loadManifestPage(),
      populateStateFilter(),
      populateCityFilter(),
      populateFilterOptions(),
    ]);
    // Populate visible dropdown with states (default active type)
    syncFilterDropdown("state");
  } catch (err) {
    if (err.status !== 401) showToast(err.message, "error");
  }
}

/* ============================================
   Wire up all event listeners
   ============================================ */
function init() {
  /* Auth forms */
  document.getElementById("login-form").addEventListener("submit", handleLogin);
  document.getElementById("register-form").addEventListener("submit", handleRegister);
  document.getElementById("show-register").addEventListener("click", () => showView("view-register"));
  document.getElementById("show-login").addEventListener("click", () => showView("view-login"));
  document.getElementById("btn-logout").addEventListener("click", handleLogout);

  /* Topbar Refresh */
  document.getElementById("btn-refresh").addEventListener("click", () => {
    loadKpis().catch(() => { });
    loadCharts().catch(() => { });
    loadManifestPage().catch(() => { });
  });

  /* Admin order modal */
  document.getElementById("btn-add-order").addEventListener("click", () => openOrderModal());
  document.getElementById("btn-close-modal").addEventListener("click", closeOrderModal);
  document.getElementById("btn-cancel-modal").addEventListener("click", closeOrderModal);
  document.getElementById("order-form").addEventListener("submit", handleSubmitOrder);
  // Close on overlay click
  document.getElementById("order-modal-overlay").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeOrderModal();
  });
  // Close on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeOrderModal();
  });

  /* Chart filters — segmented toggle (State / City) + single value dropdown */
  document.getElementById("toggle-filter-state").addEventListener("click", () => {
    if (chartFilterType === "state") return;
    activateFilterType("state");
    loadCharts().catch(() => { });
  });
  document.getElementById("toggle-filter-city").addEventListener("click", () => {
    if (chartFilterType === "city") return;
    activateFilterType("city");
    loadCharts().catch(() => { });
  });

  document.getElementById("chart-filter-value").addEventListener("change", (e) => {
    chartFilters[chartFilterType] = e.target.value;
    loadCharts().catch(() => { });
  });

  document.getElementById("btn-reset-chart-filters").addEventListener("click", () => {
    chartFilters.state = "";
    chartFilters.city  = "";
    activateFilterType("state");
    loadCharts().catch(() => { });
  });

  /* Table filters */
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

  /* Pagination */
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
    const lastOffset = Math.max(
      0,
      Math.floor((tableState.totalRows - 1) / PAGE_SIZE) * PAGE_SIZE,
    );
    tableState.offset = lastOffset;
    loadManifestPage();
  });

  /* Auto-resume session if access token exists */
  const { access } = getTokens();
  if (access) {
    enterDashboard();
  } else {
    showView("view-login");
  }
}

// Wait for loader.js to inject all view fragments before booting.
// loader.js dispatches "views:ready" after all fetch()es complete.
document.addEventListener("views:ready", init);
