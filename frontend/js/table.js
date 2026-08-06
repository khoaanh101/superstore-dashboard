"use strict";

/* ============================================
   table.js — Manifest table, pagination, order modal (admin CRUD)
   Depends on: api.js, ui.js, storage.js, charts.js (formatters)
   ============================================ */

const PAGE_SIZE = 20;
const tableState = { offset: 0, category: "", region: "", totalRows: 0 };

/* ---- HTML escape utility ---- */
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

/* ---- Filter dropdowns (category + region from API) ---- */
async function populateFilterOptions() {
  try {
    const [catRes, regRes] = await Promise.all([
      apiFetch("/query/values/category"),
      apiFetch("/query/values/region"),
    ]);

    const catSelect = document.getElementById("filter-category");
    const regSelect = document.getElementById("filter-region");

    if (catSelect) {
      const prevCat = catSelect.value;
      catSelect.innerHTML = '<option value="">All Categories</option>';
      catRes.forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c;
        opt.textContent = c;
        catSelect.appendChild(opt);
      });
      catSelect.value = prevCat || "";
    }

    if (regSelect) {
      const prevReg = regSelect.value;
      regSelect.innerHTML = '<option value="">All Regions</option>';
      regRes.forEach((r) => {
        const opt = document.createElement("option");
        opt.value = r;
        opt.textContent = r;
        regSelect.appendChild(opt);
      });
      regSelect.value = prevReg || "";
    }
  } catch (_) { /* non-critical, silently skip */ }
}


/* ---- Query builder ---- */
function buildRowsQuery() {
  const params = new URLSearchParams();
  if (tableState.category) params.set("category", tableState.category);
  if (tableState.region)   params.set("region",   tableState.region);
  params.set("limit",  String(PAGE_SIZE));
  params.set("offset", String(tableState.offset));
  return params.toString();
}

/* ---- Row rendering (role-aware: admin gets Actions column) ---- */
function renderManifestRows(rows) {
  const tbody   = document.getElementById("manifest-body");
  const { role } = getTokens();
  const isAdmin = role === "admin";
  tbody.innerHTML = "";

  if (rows.length === 0) {
    const cols = isAdmin ? 13 : 12;
    tbody.innerHTML = `<tr><td colspan="${cols}" class="empty-row">No rows matched the given filters</td></tr>`;
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
      ${isAdmin ? `<td class="action-cell">
        <button class="btn-edit"   data-id="${row.id}" title="Edit">✏️ Edit</button>
        <button class="btn-delete" data-id="${row.id}" title="Delete">🗑 Del</button>
      </td>` : ""}
    `;
    if (isAdmin) {
      tr.querySelector(".btn-edit").addEventListener("click",   () => openOrderModal(row));
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
    const res   = await apiFetch(`/query/rows?${buildRowsQuery()}`);
    const rows  = res.data;
    const total = res.total;
    tableState.totalRows = total;
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
    ["of-ship-mode",   "ship_mode"],
    ["of-segment",     "segment"],
    ["of-country",     "country"],
    ["of-city",        "city"],
    ["of-state",       "state"],
    ["of-postal-code", "postal_code"],
    ["of-region",      "region"],
    ["of-category",    "category"],
    ["of-sub-category","sub_category"],
    ["of-sales",       "sales"],
    ["of-quantity",    "quantity"],
    ["of-discount",    "discount"],
    ["of-profit",      "profit"],
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
  const errorEl   = document.getElementById("modal-error");
  const submitBtn = document.getElementById("btn-submit-order");
  errorEl.hidden      = true;
  submitBtn.disabled  = true;

  const payload = {
    ship_mode:   document.getElementById("of-ship-mode").value.trim(),
    segment:     document.getElementById("of-segment").value.trim(),
    country:     document.getElementById("of-country").value.trim(),
    city:        document.getElementById("of-city").value.trim(),
    state:       document.getElementById("of-state").value.trim(),
    postal_code: document.getElementById("of-postal-code").value.trim() || null,
    region:      document.getElementById("of-region").value.trim(),
    category:    document.getElementById("of-category").value.trim(),
    sub_category:document.getElementById("of-sub-category").value.trim(),
    sales:       parseFloat(document.getElementById("of-sales").value),
    quantity:    parseInt(document.getElementById("of-quantity").value, 10),
    discount:    parseFloat(document.getElementById("of-discount").value),
    profit:      parseFloat(document.getElementById("of-profit").value),
  };

  try {
    if (_editingOrderId !== null) {
      await apiFetch(`/orders/${_editingOrderId}`, { method: "PUT",  json: payload });
      showToast("Order updated successfully");
    } else {
      await apiFetch("/orders",                    { method: "POST", json: payload });
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
    errorEl.hidden      = false;
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

