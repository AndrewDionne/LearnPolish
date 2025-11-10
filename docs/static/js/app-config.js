// docs/static/js/app-config.js
(function (g) {
  // When hosted on GitHub Pages we must call the Render API by absolute URL.
  // When hosted on Render (same origin), leave API_BASE empty so calls are relative.
  var IS_GH = /\.github\.io$/i.test(location.hostname);
  var API_BASE = IS_GH ? 'https://path-to-polish.onrender.com' : '';
  API_BASE = (API_BASE || '').replace(/\/$/, '');

  // Optional CDN/R2 base (kept in a few synonymous fields for older code)
  var CDN_BASE = 'https://cdn.polishpath.com'.replace(/\/$/, '');

  var cfg = {
    API_BASE: API_BASE,
    CDN_BASE: CDN_BASE,

    // legacy / alt keys some pages expect:
    assetsBase: CDN_BASE,
    R2_BASE: CDN_BASE,
    cdn: CDN_BASE,
    base: CDN_BASE
  };

  // Expose under both names to keep all existing pages happy
  g.APP_CONFIG = cfg;
  g.PTP_CONFIG = g.PTP_CONFIG || cfg;

  // Also create the global identifier for scripts that reference APP_CONFIG bare
  // (not via window.APP_CONFIG). This avoids ReferenceError in such scripts.
  // eslint-disable-next-line no-var
  var APP_CONFIG = g.APP_CONFIG; // creates a real global binding in classic scripts
})(window);

// --- Ensure API_BASE is defined for all static pages ---
(function () {
  const cfg = window.APP_CONFIG || {};
  if (!cfg.API_BASE) {
    cfg.API_BASE = 'https://path-to-polish.onrender.com'; // ← your Render URL
  }
  window.APP_CONFIG = cfg;
})();
