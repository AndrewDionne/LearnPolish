// docs/offline/vocab.js
(function () {
  const S = {
    sets: [],
    currentSet: null,
    cards: [],
    index: 0,
    side: "front", // "front" | "back"
    autoplay: false,
    autoplayTimer: null,
    audio: null
  };

  // ---------- DOM helpers ----------
  const $ = (id) => document.getElementById(id);

  const elSelect = $("setSelect");
  const elDownload = $("downloadBtn");
  const elStatus = $("setStatus");
  const elSideLabel = $("sideLabel");
  const elFrontText = $("frontText");
  const elBackContent = $("backContent");
  const elPolishText = $("polishText");
  const elPronText = $("pronText");
  const elMeaningText = $("meaningText");
  const elMetaInfo = $("metaInfo");
  const btnFlip = $("flipBtn");
  const btnPrev = $("prevBtn");
  const btnNext = $("nextBtn");
  const btnPlay = $("playBtn");
  const btnAutoplay = $("autoplayBtn");

  function niceName(name) {
    return String(name || "")
      .replace(/_/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  // ---------- Service worker registration ----------
  function initServiceWorker() {
    if (!("serviceWorker" in navigator)) return;

    navigator.serviceWorker.register("sw.js").catch(() => {});

    // optional: show a small note when controller becomes active
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (!S._swReadyNotified) {
        S._swReadyNotified = true;
        if (!elStatus.textContent) {
          elStatus.textContent = "Offline caching ready. You can now download sets for offline use.";
        }
      }
    });
  }

  // ---------- Load set list ----------
  async function loadSetList() {
    try {
      const resp = await fetch("../set_modes.json", { cache: "no-cache" });
      if (!resp.ok) throw new Error("set_modes fetch failed");
      const modes = await resp.json();

      const names = Object.keys(modes || {})
        .filter((name) => {
          const arr = modes[name] || [];
          // Include vocab/speaking sets, skip pure reading-only
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
        return;
      }

      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = "Choose a set…";
      placeholder.disabled = true;
      placeholder.selected = true;
      elSelect.appendChild(placeholder);

      for (const name of names) {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = niceName(name);
        elSelect.appendChild(opt);
      }
    } catch (err) {
      console.error(err);
      elSelect.innerHTML = "";
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Error loading sets";
      elSelect.appendChild(opt);
      elSelect.disabled = true;
      elStatus.textContent = "Unable to load set list. Check connection.";
    }
  }

  // ---------- Load a specific set ----------
  async function loadSet(name) {
    if (!name) return;
    stopAutoplay();
    S.currentSet = name;
    S.cards = [];
    S.index = 0;
    S.side = "front";
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
    } catch (err) {
      console.error(err);
      S.cards = [];
      S.index = 0;
      S.side = "front";
      updateCard();
      elStatus.textContent = "Error loading set. Check connection or try again.";
      elDownload.disabled = true;
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
      elSideLabel.textContent = "Front • English";
      elFrontText.textContent = "Choose a set to begin.";
      elBackContent.style.display = "none";
      elMetaInfo.innerHTML = 'Card <strong>0</strong> of <strong>0</strong>';
      btnPlay.disabled = true;
      btnFlip.disabled = true;
      btnPrev.disabled = true;
      btnNext.disabled = true;
      btnAutoplay.disabled = true;
      return;
    }

    const { card, index } = cur;
    const meaning = card.meaning || card.english || "";
    const phrase = card.phrase || card.polish || "";
    const pron = card.pronunciation || card.pron || "";

    if (S.side === "front") {
      elSideLabel.textContent = "Front • English";
      elFrontText.textContent = meaning;
      elBackContent.style.display = "none";
    } else {
      elSideLabel.textContent = "Back • Polish";
      elFrontText.textContent = "";
      elBackContent.style.display = "";
      elPolishText.textContent = phrase;
      elPronText.textContent = pron ? `/${pron}/` : "";
      elMeaningText.textContent = meaning;
    }

    elMetaInfo.innerHTML =
      'Card <strong>' +
      (index + 1) +
      "</strong> of <strong>" +
      S.cards.length +
      "</strong>";

    const disabled = !S.cards.length;
    btnPlay.disabled = disabled;
    btnFlip.disabled = disabled;
    btnPrev.disabled = disabled;
    btnNext.disabled = disabled;
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

    // Step pattern per card:
    // 1) Flip to back
    // 2) Wait 400 ms
    // 3) Play audio
    // 4) Wait ~1600 ms
    // 5) Move to next card and repeat
    S.side = "back";
    updateCard();

    const delayBeforeAudio = 400;  // ms
    const delayAfterAudio = 1600;  // ms
    const delayBeforeNext = 600;   // front side dwell

    if (S.autoplayTimer) clearTimeout(S.autoplayTimer);

    S.autoplayTimer = setTimeout(() => {
      playCurrentAudio();
      S.autoplayTimer = setTimeout(() => {
        // Advance to next card (loop around).
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

    // Audio urls via AudioPaths (will usually be CDN-based)
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
  }

  // ---------- Event wiring ----------
  function initEvents() {
    elSelect.addEventListener("change", (e) => {
      const name = e.target.value || "";
      if (!name) return;
      loadSet(name);
    });

    btnFlip.addEventListener("click", flipCard);
    btnNext.addEventListener("click", nextCard);
    btnPrev.addEventListener("click", prevCard);
    btnPlay.addEventListener("click", () => {
      stopAutoplay();
      playCurrentAudio();
    });
    btnAutoplay.addEventListener("click", toggleAutoplay);
    elDownload.addEventListener("click", downloadCurrentSetOffline);
  }

  // ---------- Bootstrap ----------
  window.addEventListener("DOMContentLoaded", () => {
    initServiceWorker();
    initEvents();
    loadSetList();
    updateCard();
  });
})();
