"use strict";

/* ============================================
   storage.js — Token localStorage helpers + JWT decode
   ============================================ */

const STORAGE_KEYS = {
  access:  "sd_access_token",
  refresh: "sd_refresh_token",
  email:   "sd_user_email",
  role:    "sd_user_role",
};

function getTokens() {
  return {
    access:  localStorage.getItem(STORAGE_KEYS.access),
    refresh: localStorage.getItem(STORAGE_KEYS.refresh),
    email:   localStorage.getItem(STORAGE_KEYS.email),
    role:    localStorage.getItem(STORAGE_KEYS.role),
  };
}

function setTokens({ access, refresh, email, role }) {
  if (access)  localStorage.setItem(STORAGE_KEYS.access,  access);
  if (refresh) localStorage.setItem(STORAGE_KEYS.refresh, refresh);
  if (email)   localStorage.setItem(STORAGE_KEYS.email,   email);
  // Decode role from JWT if not explicitly provided
  if (access && !role) {
    role = decodeJwtRole(access);
  }
  if (role) localStorage.setItem(STORAGE_KEYS.role, role);
}

function clearTokens() {
  localStorage.removeItem(STORAGE_KEYS.access);
  localStorage.removeItem(STORAGE_KEYS.refresh);
  localStorage.removeItem(STORAGE_KEYS.email);
  localStorage.removeItem(STORAGE_KEYS.role);
}

/**
 * Decode the `role` claim from a JWT without verifying the signature.
 * Verification happens server-side; this is only for UI rendering.
 */
function decodeJwtRole(token) {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.role || "viewer";
  } catch (_) {
    return "viewer";
  }
}
