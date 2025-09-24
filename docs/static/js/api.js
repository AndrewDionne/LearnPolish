// docs/static/js/api.js
(function () {
  // For GitHub Pages, set once in the console:
  // localStorage.API_BASE = 'https://<your-render-app>.onrender.com';
  const base = (localStorage.getItem('API_BASE') || '').replace(/\/+$/, '');

  function getToken() {
    return localStorage.getItem('lp_token') || localStorage.getItem('authToken') || '';
  }

  function apiFetch(path, opts = {}) {
    const url = base + path;
    const headers = new Headers(opts.headers || {});
    const token = getToken();
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    // Token auth → no cookies
    const fetchOpts = Object.assign({ credentials: 'omit' }, opts, { headers });
    return fetch(url, fetchOpts);
  }

  window.api = { fetch: apiFetch, getToken, API_BASE: base };
})();

