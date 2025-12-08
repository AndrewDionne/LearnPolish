// docs/offline/vocab.js
(function () {
  const OFFLINE_VOCAB_KEY = "ptp_offline_vocab_sets";

  const $ = (id) => document.getElementById(id);

  const elSelect = $("setSelect");
  const elDownload = $("downloadBtn");
  const elStatus = $("setStatus");
  const elOfflineBadge = $("offlineBadge");

  const cardInner = $("cardInner");
  const elFrontText = $("frontText");
  const elPolishText = $("polishText");
  const elPronText = $("pronText");
  const elMeaningText = $("meaningText");
  const elMetaInfo = $("metaInfo");

  const btnFlip = $("flipBtn");
  const btnPrev = $("prevBtn");
  const btnNext = $("nextBtn");
  const btnPlay = $("playBtn");
  const btnAutoplay = $("autoplayBtn");

  const S = {
    sets: [],
    offlineSets: new Set(),
    currentSet: null,
    cards: [],
    index: 0,
    side: "front", // "front" | "back"
    autoplay: false,
    autoplayTimer: null,
    audio: null,
    _swReadyNotified: false
  };

  function niceName(name) {
    return String(name || "")
      .replace(/_/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  // ---------- Offline-set tracking (localStorage) ----------
  function loadOfflineSetNames() {
    try {
      const raw = localStorage.getItem(OFFLINE_VOCAB_KEY);
      if (!raw) return new Set();
      const arr = JSON.parse(raw);
      if (!Array.isArray(arr)) return new Set();
      return new Set(arr);
    } catch {
      return new Set();
    }
  }

  function saveOfflineSetNames(setNames) {
    try {
      const arr = Array.from(setNames);
      localStorage.setItem(OFFLINE_VOCAB_KEY, JSON.stringify(arr));
    } catch {
      // ignore
    }
  }

  function updateOfflineBadge() {
    if (!S.currentSet || !elOfflineBadge) {
      if (elOfflineBadge) elOfflineBadge.style.display = "none";
      return;
    }
    if (S.offlineSets.has(S.currentSet)) {
      elOfflineBadge.style.display = "inline-flex";
    } else {
      elOfflineBadge.style.display = "none";
    }
  }

  function updateSelectOptionLabels() {
    if (!elSelect || !elSelect.options) return;
    for (const opt of elSelect.options) {
      const val = opt.value;
      const baseText = opt.dataset.baseText || opt.textContent;
      if (!val) {
        opt.textContent = baseText;
        opt.dataset.baseText = baseText;
        continue;
      }
      const cleanBase = baseText.replace(/\s+• offline$/, "");
      opt.dataset.baseText = cleanBase;
      opt.textContent =
        cleanBase + (S.offlineSets.has(val) ? " • offline" : "");
    }
  }

  // ---------- Service worker ----------
  function initServiceWorker() {
    if (!("serviceWorker" in navigator)) {
      if (elStatus) {
        elStatus.textContent = "Offline caching not supported in this browser.";
      }
      return;
    }

    navigator.serviceWorker
      .register("sw.js")
      .then((reg) => {
        console.log("Offline SW registered:", reg.scope);
      })
      .catch((err) => {
        console.error("SW registration failed", err);
        if (elStatus) {
          elStatus.textContent =
            "Service Worker registration failed. Check /offline/sw.js.";
        }
      });

    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (!S._swReadyNotified) {
        S._swReadyNotified = true;
        if (!elStatus.textContent) {
          elStatus.textContent =
            "Offline caching ready. You can now download sets for offline use.";
        }
      }
    });
  }

  // ---------- Load set list ----------
  async function loadSetList() {
    S.offlineSets = loadOfflineSetNames();

    try {
      const resp = await fetch("../set_modes.json", { cache: "no-cache" });
      if (!resp.ok) throw new Error("set_modes fetch failed");
      const modes = await resp.json();

      const names = Object.keys(modes || {})
        .filter((name) => {
          const arr = modes[name] || [];
          return (
            arr.includes("flashcards") ||
            arr.includes("practice") ||
            arr.includes("learn") ||
            arr.includes("speak")
          );
        })
        .sort((a, b) => niceName(a).localeCompare(niceName(b)));

      S.sets = names;
      elSelect.innerHTML = "";

      if (!names.length) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "No vocab/speak sets available";
        elSelect.appendChild(opt);
        elSelect.disabled = true;
        elDownload.disabled = true;
        return;
      }

      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = "Choose a set…";
      placeholder.disabled = true;
      placeholder.selected = true;
      placeholder.dataset.baseText = placeholder.textContent;
      elSelect.appendChild(placeholder);

      for (const name of names) {
        const opt = document.createElement("option");
        opt.value = name;
        const base = niceName(name);
        opt.textContent = base;
        opt.dataset.baseText = base;
        if (S.offlineSets.has(name)) {
          opt.textContent = base + " • offline";
        }
        elSelect.appendChild(opt);
      }
    } catch (err) {
      console.error(err);
      elSelect.innerHTML = "";
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Error loading sets";
      opt.dataset.baseText = opt.textContent;
      elSelect.appendChild(opt);
      elSelect.disabled = true;
      elDownload.disabled = true;
      elStatus.textContent = "Unable to load set list. Check connection.";
    }
  }

  // ---------- Load a specific set ----------
  async function loadSet(name) {
    if (!name) return;

    // 🔧 HARD STOP any in-flight audio / autoplay when switching sets
    stopAutoplay();
    if (S.audio) {
      try {
        S.audio.pause();
        S.audio.currentTime = 0;
        S.audio.src = "";
      } catch (_) {}
    }
    clearTimeout(S.autoplayTimer);
    S.autoplayTimer = null;

    S.currentSet = name;
    S.cards = [];
    S.index = 0;
    S.side = "front";
    updateOfflineBadge();
    updateCard();

    elStatus.textContent = "Loading set…";
    elDownload.disabled = true;

    try {
      const url = "../sets/" + encodeURIComponent(name) + ".json";
      const resp = await fetch(url, { cache: "no-cache" });
      if (!resp.ok) throw new Error("fetch failed");
      const data = await resp.json();
      const cards = data.cards || data.items || [];

      S.cards = cards;
      S.index = 0;
      S.side = "front";
      updateCard();

      elStatus.textContent = `Loaded “${niceName(name)}” – ${cards.length} cards.`;
      elDownload.disabled = !cards.length;
      updateOfflineBadge();
    } catch (err) {
      console.error(err);
      S.cards = [];
      S.index = 0;
      S.side = "front";
      updateCard();
      elStatus.textContent = "Error loading set. Check connection or try again.";
      elDownload.disabled = true;
      updateOfflineBadge();
    }
  }

  // ---------- Card rendering ----------
  function currentCard() {
    if (!S.cards.length) return null;
    const idx = Math.max(0, Math.min(S.index, S.cards.length - 1));
    return { card: S.cards[idx], index: idx };
  }

  function updateCard() {
    const cur = currentCard();
    if (!cur) {
      elFrontText.textContent = "Choose a set to begin.";
      elFrontText.classList.remove("empty");
      elPolishText.textContent = "";
      elPronText.textContent = "";
      elMeaningText.textContent = "";
      cardInner.classList.remove("is-flipped");
      elMetaInfo.innerHTML =
        'Card <strong>0</strong> of <strong>0</strong>';
      setButtonsDisabled(true);
      return;
    }

    const { card, index } = cur;
    const meaning = card.meaning || card.english || "";
    const phrase = card.phrase || card.polish || "";
    const pron = card.pronunciation || card.pron || "";

    // Front: English
    if (meaning) {
      elFrontText.textContent = meaning;
      elFrontText.classList.remove("empty");
    } else {
      elFrontText.textContent = "(no English meaning set)";
      elFrontText.classList.add("empty");
    }

    // Back: Polish, pronunciation, meaning
    elPolishText.textContent = phrase || "";
    elPronText.textContent = pron ? `/${pron}/` : "";
    elMeaningText.textContent = meaning || "";

    // Flip state
    if (S.side === "back") {
      cardInner.classList.add("is-flipped");
    } else {
      cardInner.classList.remove("is-flipped");
    }

    elMetaInfo.innerHTML =
      'Card <strong>' +
      (index + 1) +
      "</strong> of <strong>" +
      S.cards.length +
      "</strong>";

    setButtonsDisabled(false);
  }

  function setButtonsDisabled(disabled) {
    btnFlip.disabled = disabled;
    btnPrev.disabled = disabled;
    btnNext.disabled = disabled;
    btnPlay.disabled = disabled;
    btnAutoplay.disabled = disabled;
  }

  function flipCard() {
    if (!S.cards.length) return;
    S.side = S.side === "front" ? "back" : "front";
    stopAutoplay(); // manual interaction cancels auto
    updateCard();
  }

  function nextCard() {
    if (!S.cards.length) return;
    S.index = (S.index + 1) % S.cards.length;
    S.side = "front";
    stopAutoplay();
    updateCard();
  }

  function prevCard() {
    if (!S.cards.length) return;
    S.index = (S.index - 1 + S.cards.length) % S.cards.length;
    S.side = "front";
    stopAutoplay();
    updateCard();
  }

  // ---------- Audio ----------
  function ensureAudio() {
    if (!S.audio) {
      S.audio = new Audio();
      S.audio.preload = "auto";
    }
    return S.audio;
  }

  async function playCurrentAudio() {
    const cur = currentCard();
    if (!cur || !S.currentSet) return;
    try {
      const audio = ensureAudio();
      audio.pause();
      audio.currentTime = 0;
      const src = window.AudioPaths
        ? AudioPaths.buildAudioPath(S.currentSet, cur.index, cur.card, null)
        : null;
      if (!src) return;
      audio.src = src;
      await audio.play().catch(() => {});
    } catch (err) {
      console.error("play audio failed", err);
    }
  }

  // ---------- Auto-Play ----------
  function setAutoplayUI() {
    if (S.autoplay) {
      btnAutoplay.classList.add("active");
      btnAutoplay.textContent = "Stop Auto-Play";
    } else {
      btnAutoplay.classList.remove("active");
      btnAutoplay.textContent = "Auto-Play";
    }
  }

  function stopAutoplay() {
    S.autoplay = false;
    if (S.autoplayTimer) {
      clearTimeout(S.autoplayTimer);
      S.autoplayTimer = null;
    }
    setAutoplayUI();
  }

  function startAutoplay() {
    if (!S.cards.length) return;
    S.autoplay = true;
    setAutoplayUI();
    // Always start each pass from current card front
    S.side = "front";
    updateCard();
    scheduleAutoplayStep();
  }

  function scheduleAutoplayStep() {
    if (!S.autoplay || !S.cards.length) return;

    const cur = currentCard();
    if (!cur) {
      stopAutoplay();
      return;
    }

    // Pattern per card:
    // 1) Flip to back
    // 2) Pause (400 ms)
    // 3) Play audio
    // 4) Pause (~1600 ms)
    // 5) Move to next card, briefly show front, repeat
    S.side = "back";
    updateCard();

    const delayBeforeAudio = 400;
    const delayAfterAudio = 1600;
    const delayBeforeNext = 600;

    if (S.autoplayTimer) clearTimeout(S.autoplayTimer);

    S.autoplayTimer = setTimeout(() => {
      playCurrentAudio();
      S.autoplayTimer = setTimeout(() => {
        S.index = (S.index + 1) % S.cards.length;
        S.side = "front";
        updateCard();

        if (S.autoplay) {
          S.autoplayTimer = setTimeout(scheduleAutoplayStep, delayBeforeNext);
        }
      }, delayAfterAudio);
    }, delayBeforeAudio);
  }

  function toggleAutoplay() {
    if (!S.cards.length) return;
    if (S.autoplay) {
      stopAutoplay();
    } else {
      startAutoplay();
    }
  }

  // ---------- Offline pack download ----------
  function downloadCurrentSetOffline() {
    const curSet = S.currentSet;
    if (!curSet || !S.cards.length) {
      elStatus.textContent = "Choose a set first.";
      return;
    }

    if (!("serviceWorker" in navigator)) {
      elStatus.textContent = "Offline caching not supported in this browser.";
      return;
    }

    if (!navigator.serviceWorker.controller) {
      elStatus.textContent =
        "Service Worker not active yet. Reload this page once, then try again.";
      return;
    }

    const urls = new Set();

    // Set JSON
    const jsonUrl = "../sets/" + encodeURIComponent(curSet) + ".json";
    urls.add(new URL(jsonUrl, location.href).toString());

    // Audio urls via AudioPaths
    S.cards.forEach((card, idx) => {
      try {
        if (!window.AudioPaths) return;
        const u = AudioPaths.buildAudioPath(curSet, idx, card, null);
        if (u) urls.add(new URL(u, location.href).toString());
      } catch (_) {}
    });

    const message = {
      type: "CACHE_PACK",
      pack: "vocab:" + curSet,
      urls: Array.from(urls)
    };

    navigator.serviceWorker.controller.postMessage(message);
    elStatus.textContent =
      "Downloading audio and cards for “" +
      niceName(curSet) +
      "” in the background…";

    // Mark as offline in our local list (UI indicator)
    S.offlineSets.add(curSet);
    saveOfflineSetNames(S.offlineSets);
    updateOfflineBadge();
    updateSelectOptionLabels();
  }

  // ---------- Event wiring ----------
  function initEvents() {
    if (cardInner) {
      // Click anywhere on the card to flip
      cardInner.addEventListener("click", (e) => {
        // Don’t flip if clicking on buttons on the back
        const target = e.target;
        if (target.closest("button")) return;
        flipCard();
      });
    }

    elSelect.addEventListener("change", (e) => {
      const name = e.target.value || "";
      if (!name) return;
      loadSet(name);
    });

    btnFlip.addEventListener("click", (e) => {
      e.stopPropagation();
      flipCard();
    });
    btnNext.addEventListener("click", (e) => {
      e.stopPropagation();
      nextCard();
    });
    btnPrev.addEventListener("click", (e) => {
      e.stopPropagation();
      prevCard();
    });
    btnPlay.addEventListener("click", (e) => {
      e.stopPropagation();
      stopAutoplay();
      playCurrentAudio();
    });
    btnAutoplay.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleAutoplay();
    });
    elDownload.addEventListener("click", downloadCurrentSetOffline);
  }

  // ---------- Bootstrap ----------
  window.addEventListener("DOMContentLoaded", () => {
    initServiceWorker();
    initEvents();
    loadSetList();
    updateCard();
    updateOfflineBadge();
  });
})();
