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

// --- Ensure a favicon is present on every page ---
(function () {
  try {
    if (!document.querySelector("link[rel='icon']")) {
      var root = (location.pathname.indexOf('/LearnPolish/') === 0) ? '/LearnPolish' : '';
      var link = document.createElement('link');
      link.setAttribute('rel', 'icon');
      link.setAttribute('type', 'image/svg+xml');
      link.setAttribute('href', root + '/static/brand.svg');
      document.head.appendChild(link);
    }
  } catch (_) {}
})();

// --- Load user preferences (pronunciation etc.) from localStorage ----------
(function (g) {
  if (!g || !g.localStorage) return;

  function readLocalProfile() {
    try {
      var raw = g.localStorage.getItem("lp.profile");
      if (!raw) return {};
      var obj = JSON.parse(raw);
      return obj && typeof obj === "object" ? obj : {};
    } catch (e) {
      return {};
    }
  }

  var prof = readLocalProfile();
  var prefs = (prof.preferences && typeof prof.preferences === "object")
    ? prof.preferences
    : {};

  // Back-compat: if no explicit preference, infer from older per-mode keys
  if (!prefs.pronDifficulty) {
    try {
      var dFlash = g.localStorage.getItem("lp.diff_flashcards");
      var dPractice = g.localStorage.getItem("lp.diff_practice");
      var candidate = (dFlash || dPractice || "").toLowerCase();
      if (candidate === "easy" || candidate === "normal" || candidate === "hard") {
        prefs.pronDifficulty = candidate;
        prof.preferences = prefs;
        g.localStorage.setItem("lp.profile", JSON.stringify(prof));
      }
    } catch (_e) {}
  }

  var up = g.userPrefs || {};
  if (typeof prefs.pronDifficulty === "string") {
    up.pronDifficulty = prefs.pronDifficulty.toLowerCase();
  }

  g.userPrefs = up;

  // Mirror onto APP_CONFIG if present (optional, for debugging / future use)
  if (g.APP_CONFIG) {
    g.APP_CONFIG.userPrefs = Object.assign({}, g.APP_CONFIG.userPrefs || {}, up);
  }
})(window);

