// ===== audio-paths.js =====
// Purpose: Build the correct MP3 URL for a given set + page.
// No Azure tokens. No manifest. Direct static files only.
//
// Exports a tiny helper API on window.__AudioPaths__:
//  - slugifyForFile(text)
//  - getPageContextFromPath()           // for /flashcards/<slug>/ pages
//  - getStaticBase()                    // resolves "static" base relative to current page
//  - buildAudioUrl({ mode, slug, index, nativeText })
//  - playItemAudio(audioEl, { mode, slug, index, nativeText })
//  - getSlugFromAppState()              // for SPA use (learn.html)

(function () {
  // Matches your Python sanitize_filename: lower, de-accent, non-alnum -> "_"
  function slugifyForFile(s) {
    if (!s) return "";
    s = String(s);
    // de-accent
    s = s.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    // lower
    s = s.toLowerCase();
    // non-alnum => _
    s = s.replace(/[^a-z0-9]+/g, "_");
    // collapse multiple _
    s = s.replace(/_+/g, "_");
    // trim leading/trailing _
    s = s.replace(/^_+|_+$/g, "");
    return s;
  }

  // Works for .../flashcards/<slug>/ , .../practice/<slug>/ , .../reading/<slug>/ , .../listening/<slug>/
  function getPageContextFromPath() {
    const parts = window.location.pathname.replace(/\/+$/, "").split("/");
    if (parts.length < 3) return { mode: "", slug: "" };
    const slug = parts[parts.length - 1];
    const mode = parts[parts.length - 2]; // flashcards|practice|reading|listening
    return { mode, slug };
  }

  // Determine where /static lives from the current path.
  // If we're inside /<mode>/<slug>/ -> "../../static"
  // Otherwise (SPA like /learn.html) -> "static"
  function getStaticBase() {
    const p = window.location.pathname;
    if (/(\/flashcards\/|\/practice\/|\/reading\/|\/listening\/)/.test(p)) return "../../static";
    return "static";
  }
  const STATIC_BASE = getStaticBase();

  /**
   * Build a direct MP3 path for the given item.
   * @param {Object} opts
   * @param {"flashcards"|"practice"|"reading"|"listening"} opts.mode
   * @param {string} opts.slug - set slug, e.g., "greetings"
   * @param {number} opts.index - 0-based item index
   * @param {string} [opts.nativeText] - (optional) text hint used in filename for flashcards/practice
   */
  function buildAudioUrl({ mode, slug, index, nativeText }) {
    if (!mode || !slug || typeof index !== "number") return "";

    if (mode === "reading") {
      return `${STATIC_BASE}/${slug}/reading/${index}.mp3`;
    }
    if (mode === "listening") {
      return `${STATIC_BASE}/${slug}/listening/${index}.mp3`;
    }

    // flashcards + practice share "audio" folder; filename may include a text hint
    const hint = nativeText ? `_${slugifyForFile(nativeText)}` : "";
    return `${STATIC_BASE}/${slug}/audio/${index}${hint}.mp3`;
  }

  // Ensure we have an <audio> element to play from.
  function ensureAudioElement() {
    let el = document.getElementById("player");
    if (!el) {
      el = document.createElement("audio");
      el.id = "player";
      el.preload = "none";
      document.body.appendChild(el);
    }
    return el;
  }

  /**
   * Load and play an <audio> element from a computed URL,
   * with fallback to a shorter filename (no text hint), then .wav (optional).
   */
  async function playItemAudio(audioEl, { mode, slug, index, nativeText }) {
    const el = audioEl || ensureAudioElement();
    if (!el) return;

    const primary = buildAudioUrl({ mode, slug, index, nativeText });
    const fallback = buildAudioUrl({ mode, slug, index, nativeText: "" });

    // Always reset before swapping sources
    try { el.pause(); } catch (_) {}
    try { el.currentTime = 0; } catch (_) {}

    // Try primary
    el.src = primary;
    try {
      await el.play();
      return;
    } catch (_) {
      // If primary filename used text hint and failed, try the short name
      if (primary !== fallback) {
        el.src = fallback;
        try { await el.play(); return; } catch (_) {}
      }
    }

    // Optional: last-resort try .wav (only if you also publish wavs)
    const wav = primary.replace(/\.mp3$/, ".wav");
    if (wav !== primary) {
      el.src = wav;
      try { await el.play(); return; } catch (_) {}
    }

    console.warn("Audio file not found for", { mode, slug, index, tried: [primary, fallback, wav] });
  }

  // For SPA (learn.html): try to extract slug from globals or query string.
  function getSlugFromAppState() {
    // 1) Common globals if your app sets them
    const s =
      (window.currentSet) ||
      (window.appState && window.appState.set) ||
      (window.selectedSet && (typeof window.selectedSet === "object" ? window.selectedSet : { set_name: window.selectedSet })) ||
      null;

    if (s && (s.slug || s.set_name)) {
      return s.slug || slugifyForFile(s.set_name);
    }

    // 2) URL fallback: learn.html?slug=<slug>
    const qp = new URLSearchParams(location.search);
    const fromQs = qp.get("slug");
    return fromQs ? fromQs : "";
  }

  // Expose small helpers globally so pages can call them.
  window.__AudioPaths__ = {
    slugifyForFile,
    getPageContextFromPath,
    getStaticBase,
    buildAudioUrl,
    playItemAudio,
    getSlugFromAppState,
  };
})();
