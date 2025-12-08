// docs/offline/reading.js
(function () {
  const OFFLINE_READ_KEY = "ptp_offline_read_sets";

  const $ = (id) => document.getElementById(id);

  const elSelect = $("readSetSelect");
  const elDownload = $("readDownloadBtn");
  const elStatus = $("readStatus");
  const elOfflineBadge = $("offlineBadgeRead");

  const readingCard = $("readingCard");
  const titlePl = $("titlePl");
  const titleEn = $("titleEn");
  const polishBlock = $("polishBlock");
  const englishBlock = $("englishBlock");
  const metaDialog = $("metaDialog");

  const btnPlay = $("btnPlay");
  const btnPause = $("btnPause");
  const btnReplay = $("btnReplay");
  const btnSlow = $("btnSlow");
  const btnToggleEnglish = $("btnToggleEnglish");
  const btnPrevDialog = $("btnPrevDialog");
  const btnNextDialog = $("btnNextDialog");

  const pronPanel = $("pronPanel");
  const pronWord = $("pronWord");
  const pronPhon = $("pronPhon");
  const pronClearBtn = $("pronClearBtn");

  const S = {
    sets: [],
    offlineSets: new Set(),
    currentSet: null,
    passages: [],          // [{title/title_pl/title_en, polish, english}]
    currentIndex: 0,
    audio: null,
    playbackRate: 1.0,
    wordTimer: null,
    wordSpans: [],
    _swReadyNotified: false
  };

  function niceName(name) {
    return String(name || "")
      .replace(/_/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  // ---------- Offline-set tracking ----------
  function loadOfflineSetNames() {
    try {
      const raw = localStorage.getItem(OFFLINE_READ_KEY);
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
      localStorage.setItem(OFFLINE_READ_KEY, JSON.stringify(arr));
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

  // ---------- Audio ----------
  function ensureAudio() {
    if (!S.audio) {
      S.audio = new Audio();
      S.audio.preload = "auto";
      S.audio.addEventListener("ended", () => {
        clearWordHighlight();
      });
    }
    return S.audio;
  }

  // ---------- Load available reading sets ----------
  async function loadReadingSetList() {
    S.offlineSets = loadOfflineSetNames();

    try {
      const resp = await fetch("../set_modes.json", { cache: "no-cache" });
      if (!resp.ok) throw new Error("set_modes fetch failed");
      const modes = await resp.json();

      const names = Object.keys(modes || {})
        .filter((name) => {
          const arr = modes[name] || [];
          return arr.includes("reading") || arr.includes("read");
        })
        .sort((a, b) => niceName(a).localeCompare(niceName(b)));

      S.sets = names;
      elSelect.innerHTML = "";

      if (!names.length) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "No reading sets available";
        opt.dataset.baseText = opt.textContent;
        elSelect.appendChild(opt);
        elSelect.disabled = true;
        elDownload.disabled = true;
        return;
      }

      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = "Choose a reading set…";
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
      opt.textContent = "Error loading reading sets";
      opt.dataset.baseText = opt.textContent;
      elSelect.appendChild(opt);
      elSelect.disabled = true;
      elDownload.disabled = true;
      elStatus.textContent = "Unable to load reading sets. Check connection.";
    }
  }

  // ---------- Load a specific reading set ----------
  async function loadReadingSet(name) {
    if (!name) return;

    // 🔧 HARD STOP playback + highlight when switching sets
    stopPlayback();
    clearWordHighlight();
    clearPronPanel();
    if (S.audio) {
      try {
        S.audio.pause();
        S.audio.currentTime = 0;
        S.audio.src = "";
      } catch (_) {}
    }

    S.currentSet = name;
    S.passages = [];
    S.currentIndex = 0;
    elStatus.textContent = "Loading reading set…";
    elDownload.disabled = true;
    updateOfflineBadge();

    try {
      const url = "../sets/" + encodeURIComponent(name) + ".json";
      const resp = await fetch(url, { cache: "no-cache" });
      if (!resp.ok) throw new Error("fetch failed");
      const data = await resp.json();
      const passages = (data && data.passages) || [];

      S.passages = passages;
      S.currentIndex = 0;
      renderCurrentPassage();

      elStatus.textContent =
        "Loaded “" + niceName(name) + "” – " + passages.length + " dialogues.";
      elDownload.disabled = !passages.length;
      updateOfflineBadge();
    } catch (err) {
      console.error(err);
      S.passages = [];
      S.currentIndex = 0;
      renderEmpty();
      elStatus.textContent = "Error loading reading set.";
      elDownload.disabled = true;
      updateOfflineBadge();
    }
  }

  // ---------- Rendering ----------
  function renderEmpty(message) {
    titlePl.textContent = message || "Choose a reading set to begin.";
    titleEn.textContent = "";
    polishBlock.textContent = "";
    englishBlock.textContent = "";
    readingCard.classList.remove("show-en");
    metaDialog.innerHTML = 'Dialogue <strong>0</strong> of <strong>0</strong>';
  }

  function renderCurrentPassage() {
    clearWordHighlight();
    clearPronPanel();

    if (!S.passages.length) {
      renderEmpty(
        "No passages found in this set. Choose a different one."
      );
      return;
    }

    const idx = Math.max(
      0,
      Math.min(S.currentIndex, S.passages.length - 1)
    );
    S.currentIndex = idx;
    const p = S.passages[idx];

    const title_pl = p.title_pl || p.title || "";
    const title_en =
      p.title_en || p.titleEnglish || p.title_english || "";

    titlePl.textContent = title_pl || "(no title)";
    titleEn.textContent = title_en || "";

    // Polish block with span words
    polishBlock.innerHTML = "";
    const words = String(p.polish || "").split(/\s+/).filter(Boolean);
    S.wordSpans = [];
    words.forEach((w, i) => {
      const span = document.createElement("span");
      span.className = "pl-word";
      span.dataset.wordIndex = String(i);
      span.textContent = i === words.length - 1 ? w : w + " ";
      polishBlock.appendChild(span);
      S.wordSpans.push(span);
    });

    englishBlock.textContent = p.english || "";
    readingCard.classList.remove("show-en");

    metaDialog.innerHTML =
      "Dialogue <strong>" +
      (idx + 1) +
      "</strong> of <strong>" +
      S.passages.length +
      "</strong>";

    wireWordClicks();
  }

  function wireWordClicks() {
    S.wordSpans.forEach((span) => {
      span.addEventListener("click", (evt) => {
        evt.stopPropagation();
        const text = span.textContent.replace(/\s+$/, "");
        showPronForWord(text);
        playCurrentPassage(true); // replay from start for that sentence/dialogue
      });
    });
  }

  // ---------- Word highlighting ----------
  function clearWordHighlight() {
    if (S.wordTimer) {
      clearInterval(S.wordTimer);
      S.wordTimer = null;
    }
    (S.wordSpans || []).forEach((el) => el.classList.remove("active"));
  }

  function startWordHighlight(durationSeconds) {
    clearWordHighlight();
    const spans = S.wordSpans || [];
    if (!spans.length) return;

    // Spread highlights evenly across the audio duration
    const totalMs = Math.max(durationSeconds * 1000, spans.length * 120);
    const stepMs = totalMs / spans.length;

    let i = 0;
    S.wordTimer = setInterval(() => {
      if (i >= spans.length) {
        clearWordHighlight();
        return;
      }
      spans.forEach((el, idx) => {
        el.classList.toggle("active", idx === i);
      });
      i += 1;
    }, stepMs);
  }

  // ---------- Playback ----------
  function playCurrentPassage(resetToStart = false) {
    if (!S.currentSet || !S.passages.length) return;
    const idx = S.currentIndex;
    const audio = ensureAudio();

    clearWordHighlight();

    let url = null;
    try {
      if (window.AudioPaths) {
        url = AudioPaths.readingPath(S.currentSet, idx, null);
      }
    } catch (_) {}
    if (!url) return;

    // Attach handlers before setting src
    audio.onloadedmetadata = () => {
      // Adjust highlight duration by playback rate
      const dur = audio.duration || (S.wordSpans.length * 0.4);
      const effectiveDur = dur / (audio.playbackRate || 1.0);
      startWordHighlight(effectiveDur);
    };

    audio.pause();
    audio.src = url;
    if (resetToStart) {
      audio.currentTime = 0;
    }
    audio.playbackRate = S.playbackRate;
    audio
      .play()
      .catch((err) => {
        console.error("play passage failed", err);
      });
  }

  function pausePlayback() {
    const audio = ensureAudio();
    audio.pause();
    clearWordHighlight();
  }

  function stopPlayback() {
    const audio = ensureAudio();
    audio.pause();
    audio.currentTime = 0;
    clearWordHighlight();
  }

  function replayCurrentPassage() {
    playCurrentPassage(true);
  }

  // ---------- Approximate pronunciation ----------
  function approxPron(word) {
    let w = String(word || "").toLowerCase();

    const rules = [
      [/ch/g, "h"],
      [/cz/g, "ch"],
      [/sz/g, "sh"],
      [/rz/g, "zh"],
      [/dź/g, "j"],
      [/dzi/g, "ji"],
      [/ci/g, "chi"],
      [/si/g, "shi"],
      [/ni/g, "nyi"],
      [/dz/g, "dz"],
      [/cia/g, "cha"],
      [/sia/g, "sha"],
      [/nia/g, "nya"],
      [/cię/g, "chen"],
      [/się/g, "shen"],
      [/nią/g, "nyon"],
      [/zi/g, "zhi"]
    ];

    for (const [re, rep] of rules) {
      w = w.replace(re, rep);
    }

    const single = [
      [/ą/g, "on"],
      [/ę/g, "en"],
      [/ł/g, "w"],
      [/ó/g, "oo"],
      [/ś/g, "sh"],
      [/ź/g, "zh"],
      [/ż/g, "zh"],
      [/ć/g, "ch"],
      [/ń/g, "ny"],
      [/j/g, "y"]
    ];

    for (const [re, rep] of single) {
      w = w.replace(re, rep);
    }

    return w;
  }

  function showPronForWord(word) {
    const clean = String(word || "").trim();
    if (!clean) return;
    pronWord.textContent = clean;
    pronPhon.textContent = approxPron(clean);
    pronPanel.style.display = "flex";
  }

  function clearPronPanel() {
    pronPanel.style.display = "none";
    pronWord.textContent = "";
    pronPhon.textContent = "";
  }

  // ---------- Offline caching ----------
  function downloadReadingSetOffline() {
    const curSet = S.currentSet;
    if (!curSet || !S.passages.length) {
      elStatus.textContent = "Choose a reading set first.";
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
    const jsonUrl = "../sets/" + encodeURIComponent(curSet) + ".json";
    urls.add(new URL(jsonUrl, location.href).toString());

    // All dialogue audio
    S.passages.forEach((p, idx) => {
      try {
        if (!window.AudioPaths) return;
        const u = AudioPaths.readingPath(curSet, idx, null);
        if (u) urls.add(new URL(u, location.href).toString());
      } catch (_) {}
    });

    const message = {
      type: "CACHE_PACK",
      pack: "reading:" + curSet,
      urls: Array.from(urls)
    };

    navigator.serviceWorker.controller.postMessage(message);
    elStatus.textContent =
      "Downloading audio and dialogues for “" +
      niceName(curSet) +
      "” in the background…";

    // Track as offline
    S.offlineSets.add(curSet);
    saveOfflineSetNames(S.offlineSets);
    updateOfflineBadge();
    updateSelectOptionLabels();
  }

  // ---------- Buttons / Events ----------
  function initEvents() {
    elSelect.addEventListener("change", (e) => {
      const name = e.target.value || "";
      if (!name) return;
      loadReadingSet(name);
    });

    btnPlay.addEventListener("click", () => {
      playCurrentPassage(false);
    });

    btnPause.addEventListener("click", () => {
      pausePlayback();
    });

    btnReplay.addEventListener("click", () => {
      replayCurrentPassage();
    });

    btnSlow.addEventListener("click", () => {
      S.playbackRate = S.playbackRate === 1.0 ? 0.8 : 1.0;
      btnSlow.textContent =
        S.playbackRate === 1.0 ? "0.8× Slow" : "1.0× Normal";

      // Apply immediately to current audio if playing
      if (S.audio) {
        S.audio.playbackRate = S.playbackRate;
      }
    });

    btnToggleEnglish.addEventListener("click", () => {
      const show = !readingCard.classList.contains("show-en");
      readingCard.classList.toggle("show-en", show);
      btnToggleEnglish.textContent = show ? "Hide English" : "Show English";
    });

    btnPrevDialog.addEventListener("click", () => {
      if (!S.passages.length) return;
      if (S.currentIndex <= 0) {
        S.currentIndex = S.passages.length - 1;
      } else {
        S.currentIndex -= 1;
      }
      stopPlayback();
      clearWordHighlight();
      clearPronPanel();
      renderCurrentPassage();
    });

    btnNextDialog.addEventListener("click", () => {
      if (!S.passages.length) return;
      S.currentIndex = (S.currentIndex + 1) % S.passages.length;
      stopPlayback();
      clearWordHighlight();
      clearPronPanel();
      renderCurrentPassage();
    });

    elDownload.addEventListener("click", downloadReadingSetOffline);
    pronClearBtn.addEventListener("click", clearPronPanel);
  }

  // ---------- Bootstrap ----------
  window.addEventListener("DOMContentLoaded", () => {
    initServiceWorker();
    initEvents();
    loadReadingSetList();
    renderEmpty(
      "Choose a reading set to see the dialogue and play the audio."
    );
    updateOfflineBadge();
  });
})();
