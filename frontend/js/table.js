"use strict";

/* ============================================
   table.js — Manifest table, pagination, order modal (admin CRUD)
   Depends on: api.js, ui.js, storage.js, charts.js (formatters)
   ============================================ */

const PAGE_SIZE = 20;
const tableState = {
  offset: 0,
  search_id: "",      // ID exact search
  id_from: "",        // ID range start
  id_to: "",          // ID range end
  ship_mode: "",
  segment: "",
  loc_type: "city",   // active location toggle: city | state | region
  loc_value: "",
  cat_type: "category", // active category toggle: category | sub_category
  cat_value: "",
  totalRows: 0,
  sort_by: "id",      // column to sort by (matches SortableColumn enum)
  sort_dir: "asc",   // asc | desc
};

/* ---- HTML escape utility ---- */
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

/* ---- Helper: populate a hidden select then sync the visible dropdown ---- */
async function _fillSelect(hiddenId, values, placeholder) {
  const el = document.getElementById(hiddenId);
  if (!el) return;
  el.innerHTML = `<option value="">${placeholder}</option>`;
  values.forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    el.appendChild(opt);
  });
}

/* ---- Populate all filter dropdowns from API ---- */
async function populateFilterOptions() {
  try {
    const [shipRes, segRes, cityRes, stateRes, regRes, catRes, subRes] = await Promise.all([
      apiFetch("/query/values/ship_mode"),
      apiFetch("/query/values/segment"),
      apiFetch("/query/values/city"),
      apiFetch("/query/values/state"),
      apiFetch("/query/values/region"),
      apiFetch("/query/values/category"),
      apiFetch("/query/values/sub_category"),
    ]);

    // Standalone selects
    _fillStandaloneSelect("filter-ship-mode", shipRes, "All Ship Modes");
    _fillStandaloneSelect("filter-segment", segRes, "All Segments");

    // Location hidden sources
    await Promise.all([
      _fillSelect("tbl-loc-city", cityRes, "All Cities"),
      _fillSelect("tbl-loc-state", stateRes, "All States"),
      _fillSelect("tbl-loc-region", regRes, "All Regions"),
    ]);
    syncTblLocDropdown(tableState.loc_type);

    // Category hidden sources
    await Promise.all([
      _fillSelect("tbl-cat-category", catRes, "All Categories"),
      _fillSelect("tbl-cat-subcategory", subRes, "All Sub-Categories"),
    ]);
    syncTblCatDropdown(tableState.cat_type);
  } catch (_) { /* non-critical, silently skip */ }
}

function _fillStandaloneSelect(id, values, placeholder) {
  const el = document.getElementById(id);
  if (!el) return;
  const prev = el.value;
  el.innerHTML = `<option value="">${placeholder}</option>`;
  values.forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    el.appendChild(opt);
  });
  el.value = prev || "";
}

/* ---- Sync visible location dropdown from hidden source ---- */
function syncTblLocDropdown(type) {
  const sourceId = { city: "tbl-loc-city", state: "tbl-loc-state", region: "tbl-loc-region" }[type];
  const placeholder = { city: "All Cities", state: "All States", region: "All Regions" }[type];
  const source = document.getElementById(sourceId);
  const visible = document.getElementById("tbl-loc-value");
  if (!source || !visible) return;
  const prev = tableState.loc_value;
  visible.innerHTML = `<option value="">${placeholder}</option>`;
  for (const opt of source.options) {
    if (!opt.value) continue;
    const o = document.createElement("option");
    o.value = opt.value;
    o.textContent = opt.textContent;
    if (opt.value === prev) o.selected = true;
    visible.appendChild(o);
  }
  visible.value = prev || "";
}

/* ---- Sync visible category dropdown from hidden source ---- */
function syncTblCatDropdown(type) {
  const sourceId = type === "category" ? "tbl-cat-category" : "tbl-cat-subcategory";
  const placeholder = type === "category" ? "All Categories" : "All Sub-Categories";
  const source = document.getElementById(sourceId);
  const visible = document.getElementById("tbl-cat-value");
  if (!source || !visible) return;
  const prev = tableState.cat_value;
  visible.innerHTML = `<option value="">${placeholder}</option>`;
  for (const opt of source.options) {
    if (!opt.value) continue;
    const o = document.createElement("option");
    o.value = opt.value;
    o.textContent = opt.textContent;
    if (opt.value === prev) o.selected = true;
    visible.appendChild(o);
  }
  visible.value = prev || "";
}

/* ---- Activate a location toggle button ---- */
function activateTblLocType(type) {
  tableState.loc_type = type;
  tableState.loc_value = "";
  ["city", "state", "region"].forEach((t) => {
    document.getElementById(`tbl-toggle-${t}`)?.classList.toggle("is-active", t === type);
  });
  syncTblLocDropdown(type);
}

/* ---- Activate a category toggle button ---- */
function activateTblCatType(type) {
  tableState.cat_type = type;
  tableState.cat_value = "";
  const label = type === "category" ? "category" : "subcategory";
  ["category", "subcategory"].forEach((t) => {
    document.getElementById(`tbl-toggle-${t}`)?.classList.toggle("is-active", t === label);
  });
  syncTblCatDropdown(type);
}


/* ---- Query builder ---- */
function buildRowsQuery() {
  const params = new URLSearchParams();
  if (tableState.search_id) params.set("id", tableState.search_id);
  if (tableState.id_from) params.set("id_from", tableState.id_from);
  if (tableState.id_to) params.set("id_to", tableState.id_to);
  if (tableState.ship_mode) params.set("ship_mode", tableState.ship_mode);
  if (tableState.segment) params.set("segment", tableState.segment);
  if (tableState.loc_value) params.set(tableState.loc_type, tableState.loc_value);
  if (tableState.cat_value) params.set(tableState.cat_type, tableState.cat_value);
  params.set("sort_by", tableState.sort_by);
  params.set("sort_dir", tableState.sort_dir);
  params.set("limit", String(PAGE_SIZE));
  params.set("offset", String(tableState.offset));
  return params.toString();
}

/* ---- Update sort indicator icons on thead ---- */
function updateSortIndicators() {
  document.querySelectorAll("thead th.sortable").forEach((th) => {
    const key = th.dataset.sortKey;
    const icon = th.querySelector(".sort-icon");
    if (!icon) return;
    if (key === tableState.sort_by) {
      icon.textContent = tableState.sort_dir === "asc" ? " ▲" : " ▼";
      th.classList.add("is-sorted");
    } else {
      icon.textContent = "";
      th.classList.remove("is-sorted");
    }
  });
}

/* ---- Sort click handler (event delegation on thead) ---- */
function initSortHandlers() {
  const thead = document.querySelector(".manifest thead");
  if (!thead) return;
  thead.addEventListener("click", (e) => {
    const th = e.target.closest("th.sortable");
    if (!th) return;
    const key = th.dataset.sortKey;
    if (!key) return;
    if (tableState.sort_by === key) {
      tableState.sort_dir = tableState.sort_dir === "asc" ? "desc" : "asc";
    } else {
      tableState.sort_by = key;
      tableState.sort_dir = "asc";
    }
    tableState.offset = 0;
    updateSortIndicators();
    loadManifestPage();
  });
}

/* ---- Row rendering (role-aware: admin gets Actions column) ---- */
function renderManifestRows(rows) {
  const tbody = document.getElementById("manifest-body");
  const { role } = getTokens();
  const isAdmin = role === "admin";
  tbody.innerHTML = "";

  if (rows.length === 0) {
    const cols = isAdmin ? 14 : 13;
    tbody.innerHTML = `<tr><td colspan="${cols}" class="empty-row">No rows matched the given filters</td></tr>`;
    return;
  }

  for (const [idx, row] of rows.entries()) {
    const stt = tableState.offset + idx + 1;
    const tr = document.createElement("tr");
    const profitClass = row.profit >= 0 ? "profit-pos" : "profit-neg";
    tr.innerHTML = `
      <td class="col-stt">${stt}</td>
      <td class="col-hide-sm">${row.id}</td>
      <td>${escapeHtml(row.ship_mode)}</td>
      <td>${escapeHtml(row.segment)}</td>
      <td>${escapeHtml(row.city)}</td>
      <td class="col-hide-md">${escapeHtml(row.state)}</td>
      <td class="col-hide-md">${escapeHtml(row.region)}</td>
      <td class="col-hide-md">${escapeHtml(row.category)}</td>
      <td class="col-hide-md">${escapeHtml(row.sub_category)}</td>
      <td class="num">${formatCurrency(row.sales)}</td>
      <td class="num col-hide-md">${formatNumber(row.quantity)}</td>
      <td class="num col-hide-md">${(row.discount * 100).toFixed(0)}%</td>
      <td class="num ${profitClass}">${formatCurrency(row.profit)}</td>
      ${isAdmin ? `<td class="action-cell">
        <button class="btn-edit"   data-id="${row.id}" title="Edit">✏️ Edit</button>
        <button class="btn-delete" data-id="${row.id}" title="Delete">🗑 Del</button>
      </td>` : ""}
    `;
    if (isAdmin) {
      tr.querySelector(".btn-edit").addEventListener("click", () => openOrderModal(row));
      tr.querySelector(".btn-delete").addEventListener("click", () => confirmDeleteOrder(row.id));
    }
    tbody.appendChild(tr);
  }
}

/* ---- Page load ---- */
async function loadManifestPage() {
  const tbody = document.getElementById("manifest-body");

  // Fade the current rows in-place — no layout shift, no scroll reset
  tbody.classList.add("is-loading");

  // Disable pagination buttons while fetching
  ["btn-first", "btn-prev", "btn-next", "btn-last"].forEach((id) => {
    document.getElementById(id).disabled = true;
  });

  try {
    const res = await apiFetch(`/query/rows?${buildRowsQuery()}`);
    const rows = res.data;
    const total = res.total;
    tableState.totalRows = total;
    renderManifestRows(rows);

    const from = rows.length === 0 ? 0 : tableState.offset + 1;
    const to = tableState.offset + rows.length;
    document.getElementById("page-indicator").textContent =
      rows.length === 0 ? "No data" : `Showing ${from}–${to} of ${formatNumber(total)}`;

    const isFirst = tableState.offset === 0;
    const isLast = rows.length < PAGE_SIZE;
    document.getElementById("btn-first").disabled = isFirst;
    document.getElementById("btn-prev").disabled = isFirst;
    document.getElementById("btn-next").disabled = isLast;
    document.getElementById("btn-last").disabled = isLast;
  } catch (err) {
    if (err.status === 404) {
      renderManifestRows([]);
      document.getElementById("page-indicator").textContent = "No data";
      ["btn-first", "btn-prev"].forEach((id) =>
        (document.getElementById(id).disabled = tableState.offset === 0));
      ["btn-next", "btn-last"].forEach((id) =>
        (document.getElementById(id).disabled = true));
    } else {
      tbody.innerHTML = `<tr><td colspan="12" class="empty-row">Error: ${escapeHtml(err.message)}</td></tr>`;
    }
  } finally {
    tbody.classList.remove("is-loading");
  }
}

/* ---- Reset all table filters to default ---- */
function resetTableFilters() {
  // Reset state
  tableState.offset = 0;
  tableState.search_id = "";
  tableState.id_from = "";
  tableState.id_to = "";
  tableState.ship_mode = "";
  tableState.segment = "";
  tableState.loc_type = "city";
  tableState.loc_value = "";
  tableState.cat_type = "category";
  tableState.cat_value = "";
  tableState.sort_by = "id";
  tableState.sort_dir = "asc";

  // Sync UI — inputs
  const searchInput = document.getElementById("search-manifest");
  if (searchInput) { searchInput.value = ""; }
  const clearBtn = document.getElementById("btn-clear-search");
  if (clearBtn) clearBtn.hidden = true;
  const idFrom = document.getElementById("input-id-from");
  if (idFrom) idFrom.value = "";
  const idTo = document.getElementById("input-id-to");
  if (idTo) idTo.value = "";
  const clearRange = document.getElementById("btn-clear-range");
  if (clearRange) clearRange.hidden = true;

  // Sync UI — standalone dropdowns
  const shipMode = document.getElementById("filter-ship-mode");
  if (shipMode) shipMode.value = "";
  const segment = document.getElementById("filter-segment");
  if (segment) segment.value = "";

  // Sync UI — location toggle back to City (default)
  activateTblLocType("city");

  // Sync UI — category toggle back to Category (default)
  activateTblCatType("category");

  // Sync sort indicators
  updateSortIndicators();

  loadManifestPage();
}

/* ---- Export current filtered data as CSV ---- */
async function exportTableCsv() {
  const params = new URLSearchParams();
  if (tableState.search_id) params.set("id", tableState.search_id);
  if (tableState.id_from) params.set("id_from", tableState.id_from);
  if (tableState.id_to) params.set("id_to", tableState.id_to);
  if (tableState.ship_mode) params.set("ship_mode", tableState.ship_mode);
  if (tableState.segment) params.set("segment", tableState.segment);
  if (tableState.loc_value) params.set(tableState.loc_type, tableState.loc_value);
  if (tableState.cat_value) params.set(tableState.cat_type, tableState.cat_value);
  params.set("sort_by", tableState.sort_by);
  params.set("sort_dir", tableState.sort_dir);

  const { access } = getTokens();
  const btn = document.getElementById("btn-export-csv");
  const originalText = btn ? btn.textContent : "";
  if (btn) { btn.disabled = true; btn.textContent = "Exporting..."; }

  try {
    const res = await fetch(
      `${API_BASE_URL}/query/rows/export?${params.toString()}`,
      { headers: access ? { Authorization: `Bearer ${access}` } : {} },
    );
    if (!res.ok) {
      const detail = await res.text().catch(() => res.statusText);
      showToast(`Export failed: ${detail}`, "error");
      return;
    }
    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = "superstore_export.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(blobUrl);
  } catch (err) {
    showToast(`Export failed: ${err.message}`, "error");
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = originalText; }
  }
}

/* ---- Debounce utility ---- */
function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

/* ---- ID Search handler (wired in app.js) ---- */
function applySearch(value) {
  const trimmed = String(value).trim();
  // Accept only positive integers; anything else clears the filter
  tableState.search_id = /^\d+$/.test(trimmed) ? trimmed : "";
  tableState.offset = 0;
  const clearBtn = document.getElementById("btn-clear-search");
  if (clearBtn) clearBtn.hidden = !tableState.search_id;
  loadManifestPage();
}

const debouncedSearch = debounce((value) => applySearch(value), 350);


/* ============================================
   Order Modal — Add / Edit (admin only)
   ============================================ */
let _editingOrderId = null; // null = creating, number = editing

/** Open modal. Pass a row object to edit it, or null to create new. */
function openOrderModal(row = null) {
  _editingOrderId = row ? row.id : null;
  document.getElementById("modal-title").textContent = row ? "Edit Order" : "Add Order";

  // Map field IDs → data keys
  const fields = [
    ["of-ship-mode", "ship_mode"],
    ["of-segment", "segment"],
    ["of-country", "country"],
    ["of-city", "city"],
    ["of-state", "state"],
    ["of-postal-code", "postal_code"],
    ["of-region", "region"],
    ["of-category", "category"],
    ["of-sub-category", "sub_category"],
    ["of-sales", "sales"],
    ["of-quantity", "quantity"],
    ["of-discount", "discount"],
    ["of-profit", "profit"],
  ];
  fields.forEach(([elId, key]) => {
    document.getElementById(elId).value = row ? (row[key] ?? "") : "";
  });

  document.getElementById("modal-error").hidden = true;
  document.getElementById("order-modal-overlay").hidden = false;
}

function closeOrderModal() {
  document.getElementById("order-modal-overlay").hidden = true;
  document.getElementById("order-form").reset();
  _editingOrderId = null;
}

async function handleSubmitOrder(evt) {
  evt.preventDefault();
  const errorEl = document.getElementById("modal-error");
  const submitBtn = document.getElementById("btn-submit-order");
  errorEl.hidden = true;
  submitBtn.disabled = true;

  const payload = {
    ship_mode: document.getElementById("of-ship-mode").value.trim(),
    segment: document.getElementById("of-segment").value.trim(),
    country: document.getElementById("of-country").value.trim(),
    city: document.getElementById("of-city").value.trim(),
    state: document.getElementById("of-state").value.trim(),
    postal_code: document.getElementById("of-postal-code").value.trim() || null,
    region: document.getElementById("of-region").value.trim(),
    category: document.getElementById("of-category").value.trim(),
    sub_category: document.getElementById("of-sub-category").value.trim(),
    sales: parseFloat(document.getElementById("of-sales").value),
    quantity: parseInt(document.getElementById("of-quantity").value, 10),
    discount: parseFloat(document.getElementById("of-discount").value),
    profit: parseFloat(document.getElementById("of-profit").value),
  };

  try {
    if (_editingOrderId !== null) {
      await apiFetch(`/orders/${_editingOrderId}`, { method: "PUT", json: payload });
      showToast("Order updated successfully");
    } else {
      await apiFetch("/orders", { method: "POST", json: payload });
      showToast("Order created successfully");
    }
    closeOrderModal();
    tableState.offset = 0;
    await Promise.all([
      loadManifestPage(),
      typeof loadKpis === "function" ? loadKpis() : Promise.resolve(),
      typeof loadCharts === "function" ? loadCharts() : Promise.resolve(),
      typeof loadRegionDonut === "function" ? loadRegionDonut() : Promise.resolve(),
      typeof populateStateFilter === "function" ? populateStateFilter() : Promise.resolve(),
      typeof populateCityFilter === "function" ? populateCityFilter() : Promise.resolve(),
      typeof populateFilterOptions === "function" ? populateFilterOptions() : Promise.resolve(),
    ]);
    if (typeof syncFilterDropdown === "function") {
      syncFilterDropdown(chartFilterType);
    }
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.hidden = false;
  } finally {
    submitBtn.disabled = false;
  }
}

async function confirmDeleteOrder(orderId) {
  if (!confirm(`Delete order #${orderId}? This cannot be undone.`)) return;
  try {
    await apiFetch(`/orders/${orderId}`, { method: "DELETE" });
    showToast("Order deleted");
    await Promise.all([
      loadManifestPage(),
      typeof loadKpis === "function" ? loadKpis() : Promise.resolve(),
      typeof loadCharts === "function" ? loadCharts() : Promise.resolve(),
      typeof loadRegionDonut === "function" ? loadRegionDonut() : Promise.resolve(),
      typeof populateStateFilter === "function" ? populateStateFilter() : Promise.resolve(),
      typeof populateCityFilter === "function" ? populateCityFilter() : Promise.resolve(),
      typeof populateFilterOptions === "function" ? populateFilterOptions() : Promise.resolve(),
    ]);
    if (typeof syncFilterDropdown === "function") {
      syncFilterDropdown(chartFilterType);
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

