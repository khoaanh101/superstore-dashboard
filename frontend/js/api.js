"use strict";

/* ============================================
   api.js — HTTP layer with auth + silent token refresh
   Depends on: storage.js, ui.js (forceLogout)
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
  } catch (_networkErr) {
    throw new ApiError("Cannot connect to server", 0);
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
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ refresh_token: refresh }),
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
