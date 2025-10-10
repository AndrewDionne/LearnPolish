// docs/static/js/api.js
(function () {
  // ---- Small helpers -------------------------------------------------------
  const stripTrail = (s) => (s || '').replace(/\/+$/, '');
  const ensureLead = (s) => (s && s.startsWith('/') ? s : '/' + (s || ''));

  // ---- Configuration -------------------------------------------------------
  // Accept either name; some pages set APP_CONFIG, others PTP_CONFIG.
  const RUNTIME = (typeof window !== 'undefined' ? (window.APP_CONFIG || window.PTP_CONFIG || {}) : {});
  const CONFIG_API_BASE = stripTrail(RUNTIME.API_BASE || '');
  const CONFIG_CDN_BASE = stripTrail(
    RUNTIME.CDN_BASE || RUNTIME.assetsBase || RUNTIME.R2_BASE || RUNTIME.cdn || RUNTIME.base || ''
  );

  // Single source of truth when not same-origin
  const DEFAULT_RENDER_API = CONFIG_API_BASE || 'https://path-to-polish.onrender.com';
  const CDN_BASE = CONFIG_CDN_BASE;

  function detectApiBase() {
    // Manual override for debugging
    const override = stripTrail(localStorage.getItem('API_BASE') || '');
    if (override) return override;

    const host = (typeof location !== 'undefined' ? location.hostname : '');
    const isGH    = /\.github\.io$/i.test(host);
    const isLocal = /^(localhost|127\.0\.0\.1)$/i.test(host);
    const isRender= /onrender\.com$/i.test(host);

    if (isGH) return DEFAULT_RENDER_API; // static frontend → remote API
    if (isLocal || isRender) return '';  // same-origin on dev or Render
    return DEFAULT_RENDER_API;           // safe fallback
  }

  const API_BASE = stripTrail(detectApiBase());

  // ---- Token helpers -------------------------------------------------------
  function getToken() {
    return localStorage.getItem('lp_token')
        || localStorage.getItem('authToken')
        || '';
  }
  function setToken(tok) {
    if (!tok) return;
    try { localStorage.setItem('lp_token', tok); } catch {}
    try { localStorage.setItem('authToken', tok); } catch {}
  }
  function clearToken() {
    try { localStorage.removeItem('lp_token'); } catch {}
    try { localStorage.removeItem('authToken'); } catch {}
  }

  // ---- Fetch core ----------------------------------------------------------
  function joinUrl(base, path) {
    if (/^https?:\/\//i.test(path)) return path; // already absolute
    const p = ensureLead(path || '/');
    return base ? stripTrail(base) + p : p;
  }

  async function apiFetch(path, opts = {}) {
    const url = joinUrl(API_BASE, path);
    const headers = new Headers(opts.headers || {});
    const token = getToken();
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    let body = opts.body;
    if (opts.json !== undefined) {
      if (!headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json; charset=utf-8');
      }
      body = JSON.stringify(opts.json);
    }

    const fetchOpts = Object.assign(
      { method: opts.method || 'GET', credentials: 'omit', mode: 'cors', cache: 'no-store' },
      opts,
      { headers, body }
    );

    return fetch(url, fetchOpts);
  }

  // ---- JSON helpers --------------------------------------------------------
  async function requestJSON(path, opts = {}) {
    const res = await apiFetch(path, opts);
    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try { const j = await res.json(); msg = j.message || j.error || msg; } catch {}
      const e = new Error(msg);
      e.status = res.status;
      throw e;
    }
    const ct = (res.headers.get('Content-Type') || '').toLowerCase();
    if (ct.includes('application/json')) return res.json();
    return null; // allow 204s / non-JSON OKs
  }
  const get   = (p, o={}) => requestJSON(p, o);
  const post  = (p, json) => requestJSON(p, { method: 'POST', json });
  const put   = (p, json) => requestJSON(p, { method: 'PUT',  json });
  const patch = (p, json) => requestJSON(p, { method: 'PATCH',json });
  const del   = (p, json) => requestJSON(p, { method: 'DELETE', json });

  // ---- Auth helper ---------------------------------------------------------
  async function requireAuth(loginFile = 'login.html') {
    try {
      await get('/api/me');
      return true;
    } catch (e) {
      if (e && e.status === 401) {
        const root = location.pathname.startsWith('/LearnPolish/') ? '/LearnPolish/' : '/';
        location.href = root + loginFile;
        return false;
      }
      throw e;
    }
  }

  // ---- Media (CDN) helper --------------------------------------------------
  function mediaUrl(relPath) {
    const p = ensureLead(relPath || '');
    return CDN_BASE ? (CDN_BASE + p) : p;
  }

  // ---- Lightweight ping (debug) -------------------------------------------
  apiFetch('/api/token')
    .then(r => { if (!r.ok) throw 0; })
    .catch(() => console.warn('[api] Ping failed. Check API_BASE:', API_BASE));

  // ---- Public API ----------------------------------------------------------
  window.api = window.api || {
    fetch: apiFetch,
    get, post, put, patch, del,
    getToken, setToken, clearToken,
    requireAuth,
    mediaUrl,
    API_BASE,
    CDN_BASE
  };
})();
