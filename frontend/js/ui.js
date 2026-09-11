"use strict";

/* ============================================
   ui.js — View switching, toast, form helpers
   Depends on: storage.js
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

/* ---- Toast ---- */
let _toastTimer = null;

function showToast(message, kind = "default") {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = "toast" + (kind === "error" ? " toast--error" : "");
  toast.hidden = false;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => { toast.hidden = true; }, 4000);
}

/* ---- Form error helper ---- */
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
