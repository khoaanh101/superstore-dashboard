"use strict";

/* ============================================
   loader.js — HTML view fragment loader
   Fetches each view partial from /frontend/views/
   and injects it into #app-root synchronously
   (via document.write-safe inline script trick)
   before app.js boots.

   Load order in index.html:
     ... other scripts ...
     <script src="loader.js"></script>   ← runs & awaits fragments
     <script src="app.js"></script>      ← runs after DOMContentLoaded
   ============================================ */

(function () {
  /**
   * Fetch an HTML fragment and inject it into the app root.
   * Returns a Promise that resolves when the fragment is in the DOM.
   */
  async function loadFragment(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`Failed to load view: ${path} (${res.status})`);
    const html = await res.text();
    const root = document.getElementById("app-root");
    root.insertAdjacentHTML("beforeend", html);
  }

  /**
   * All view fragments to load, in DOM order.
   * Add new views here — no changes to index.html needed.
   */
  const VIEW_FRAGMENTS = [
    "/frontend/views/view-login.html",
    "/frontend/views/view-register.html",
    "/frontend/views/view-dashboard.html",
    "/frontend/views/modal-order.html",
  ];

  /**
   * Block app boot until all fragments are injected.
   * We attach a custom event "views:ready" that app.js listens for
   * instead of DOMContentLoaded (which fires before fragments arrive).
   */
  async function loadAllFragments() {
    try {
      await Promise.all(VIEW_FRAGMENTS.map(loadFragment));
    } catch (err) {
      // Show a minimal error state if fragments fail to load
      document.getElementById("app-root").innerHTML = `
        <div style="display:flex;align-items:center;justify-content:center;min-height:100vh;
          font-family:sans-serif;color:#A32D2D;padding:32px;text-align:center;">
          <div>
            <p style="font-size:18px;font-weight:700;margin-bottom:8px;">Failed to load application</p>
            <p style="font-size:14px;color:#6B6F76;">${err.message}</p>
          </div>
        </div>`;
      throw err;
    }
    document.dispatchEvent(new CustomEvent("views:ready"));
  }

  // Start loading immediately (non-blocking for parser, but Promises run in microtask queue)
  loadAllFragments();
})();
