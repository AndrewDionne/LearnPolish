// ===== flashcards-audio-adapter.js =====
// Redirects any flashcard "speak" action to static MP3 playback via __AudioPaths__.

(function () {
  function getSlug() {
    return (window.__AudioPaths__ &&
      (window.__AudioPaths__.getSlugFromAppState() || window.__AudioPaths__.getPageContextFromPath().slug)) || "";
  }

  async function playFromStatic(index, nativeText) {
    const slug = getSlug();
    if (!slug) {
      console.warn("No slug found for audio playback");
      return;
    }
    await window.__AudioPaths__.playItemAudio(null, {
      mode: "flashcards",
      slug,
      index,
      nativeText
    });
  }

  // 1) If your app exposes a "speak" function, override it.
  //    (These are common names; only the ones that exist will be replaced.)
  ["speakNative", "playNative", "speakText", "playItemAudio"].forEach((name) => {
    if (typeof window[name] === "function") {
      const orig = window[name];
      window[name] = function (...args) {
        // Heuristics: try (text, index) or (index, text) or (item)
        let text = "", index = (window.currentIndex ?? 0);
        if (args.length === 2) {
          // either (text, index) OR (index, text)
          if (typeof args[0] === "string" && typeof args[1] === "number") {
            text = args[0]; index = args[1];
          } else if (typeof args[0] === "number") {
            index = args[0]; text = String(args[1] ?? "");
          }
        } else if (args.length === 1 && typeof args[0] === "object" && args[0]) {
          const it = args[0];
          index = it.index ?? index;
          text = it.native ?? it.native_text ?? it.text ?? "";
        }
        return playFromStatic(index, text);
      };
    }
  });

  // 2) Generic click delegation fallback (if there is no global function).
  //    Works with buttons like:
  //    <button class="speak-btn" data-index="3" data-native="Cześć">▶</button>
  document.addEventListener("click", (e) => {
    const btn = e.target.closest('[data-action="speak"], .speak-btn, .play-audio');
    if (!btn) return;
    const raw = btn.getAttribute("data-index") || btn.dataset.index;
    const index = raw ? parseInt(raw, 10) : (window.currentIndex ?? 0);
    const text =
      btn.getAttribute("data-native") ||
      btn.dataset.native ||
      (window.currentCard && (window.currentCard.native || window.currentCard.native_text)) ||
      "";
    playFromStatic(index, text);
    e.preventDefault();
  });
})();
