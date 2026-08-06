"use strict";

/* ============================================
   auth.js — Login, Register, Logout handlers
   Depends on: storage.js, api.js, ui.js
   ============================================ */

async function handleLogin(evt) {
  evt.preventDefault();
  setFormError("login-error", "");
  const email     = document.getElementById("login-email").value.trim();
  const password  = document.getElementById("login-password").value;
  const submitBtn = document.getElementById("login-submit");

  submitBtn.disabled = true;
  try {
    const data = await apiFetch("/auth/token", {
      method: "POST",
      form:   { username: email, password },
      retry:  false,
    });
    setTokens({ access: data.access_token, refresh: data.refresh_token, email });
    await enterDashboard();
  } catch (err) {
    setFormError(
      "login-error",
      err.status === 401 ? "Invalid email/password" : err.message,
    );
  } finally {
    submitBtn.disabled = false;
  }
}

async function handleRegister(evt) {
  evt.preventDefault();
  setFormError("register-error", "");
  document.getElementById("register-success").hidden = true;
  const email     = document.getElementById("register-email").value.trim();
  const password  = document.getElementById("register-password").value;
  const submitBtn = document.getElementById("register-submit");

  submitBtn.disabled = true;
  try {
    await apiFetch("/auth/register", {
      method: "POST",
      json:   { email, password },
      retry:  false,
    });
    const successEl = document.getElementById("register-success");
    successEl.hidden = false;
    successEl.textContent = "Registration completed. You can log in now.";
    document.getElementById("register-form").reset();
  } catch (err) {
    setFormError(
      "register-error",
      err.status === 400 ? "This email has already been registered" : err.message,
    );
  } finally {
    submitBtn.disabled = false;
  }
}

async function handleLogout() {
  const { refresh } = getTokens();
  if (refresh) {
    try {
      await apiFetch("/auth/logout", {
        method: "POST",
        json:   { refresh_token: refresh },
        retry:  false,
      });
    } catch (_) {
      /* best-effort revoke; proceed with local logout regardless */
    }
  }
  clearTokens();
  showView("view-login");
}
