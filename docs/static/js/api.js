// docs/static/js/api.js
(function () {
  // ---- Configuration -------------------------------------------------------
  // Default API when running on GitHub Pages (overrideable via localStorage.API_BASE)
  const DEFAULT_RENDER_API = 'https://flashcards-5c95.onrender.com';

  // Optional CDN base for media (R2). You can set this in the console:
  //   localStorage.CDN_BASE = 'https://<your-r2-public-domain>/<bucket>'
  const CDN_BASE = (localStorage.getItem('CDN_BASE') || '').replace(/\/+$/, '');

  // ---- Utilities -----------------------------------------------------------
  const stripTrail = (s) => (s || '').replace(/\/+$/, '');
  const ensureLead = (s) => (s.startsWith('/') ? s : '/' + s);

  function detectApiBase() {
    const override = stripTrail(localStorage.getItem('API_BASE') || '');
    if (override) return override;

    const host = location.hostname;
    const isGH = /\.github\.io$/i.test(host);
    const isLocal = /^(localhost|127\.0\.0\.1)$/i.test(host);
    const isRender = /onrender\.com$/i.test(host);

    if (isGH) return DEFAULT_RENDER_API; // static frontend → remote API
    if (isLocal || isRender) return '';  // same-origin API during dev or on Render
    return DEFAULT_RENDER_API;           // safe fallback
  }

  const API_BASE = detectApiBase();

  function getToken() {
    return localStorage.getItem('lp_token')
        || localStorage.getItem('authToken')
        || '';
  }
  function setToken(tok) {
    if (!tok) return;
    localStorage.setItem('lp_token', tok);
    localStorage.setItem('authToken', tok);
  }
  function clearToken() {
    localStorage.removeItem('lp_token');
    localStorage.removeItem('authToken');
  }

  function joinUrl(base, path) {
    const p = ensureLead(path || '/');
    return base ? stripTrail(base) + p : p;
  }

  // Core fetch (adds Authorization, sane defaults, JSON shortcut)
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

  // JSON helpers
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
    // allow empty 204, or non-JSON OK
    return null;
  }
  const get  = (p, o={}) => requestJSON(p, o);
  const post = (p, json) => requestJSON(p, { method: 'POST', json });
  const put  = (p, json) => requestJSON(p, { method: 'PUT',  json });
  const patch= (p, json) => requestJSON(p, { method: 'PATCH',json });
  const del  = (p, json) => requestJSON(p, { method: 'DELETE', json });

  // Simple auth check you can call at page load; on 401 redirect to login
  async function requireAuth(loginFile = 'login.html') {
    try {
      await get('/api/me');
      return true;
    } catch (e) {
      if (e && e.status === 401) {
        // If on GitHub Pages under /LearnPolish/, keep the subpath
        const root = location.pathname.startsWith('/LearnPolish/')
          ? '/LearnPolish/' : '/';
        location.href = root + loginFile;
        return false;
      }
      throw e;
    }
  }

  // Build media (R2) absolute URL from a relative path like "audio/foo.mp3"
  function mediaUrl(relPath) {
    const p = ensureLead(relPath || '');
    return CDN_BASE ? (CDN_BASE + p) : p;
  }

  // Quick health check (non-fatal)
  apiFetch('/ping')
    .then(r => { if (!r.ok) throw 0; })
    .catch(() => console.warn('[api] Ping failed. Check API_BASE:', API_BASE));

  // Public API
  window.api = {
    fetch: apiFetch,
    get, post, put, patch, del,
    getToken, setToken, clearToken,
    requireAuth,
    mediaUrl,
    API_BASE: API_BASE,
    CDN_BASE: CDN_BASE
  };
})();
