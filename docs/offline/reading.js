// docs/offline/reading.js
(function () {
  const $ = (id) => document.getElementById(id);

  const elSelect = $("readSetSelect");
  const elDownload = $("readDownloadBtn");
  const elStatus = $("readStatus");
  const elPassages = $("passages");
  const btnPlayAll = $("btnPlayAll");
  const btnPause = $("btnPause");
  const btnReplay = $("btnReplay");
  const btnSlow = $("btnSlow");
  const btnToggleEnglish = $("btnToggleEnglish");
  const pronPanel = $("pronPanel");
  const pronWord = $("pronWord");
  const pronPhon = $("pronPhon");
  const pronClearBtn = $("pronClearBtn");

  const S = {
    sets: [],
    currentSet: null,
    passages: [], // [{polish,english,title}]
    audio: null,
    playbackRate: 1.0,
    seqIndex: 0,
    playingSequence: false,
    wordTimer: null,
    wordSpans: {}, // segIndex -> [span,...]
    activeSeg: null
  };

  function niceName(name) {
    return String(name || "")
      .replace(/_/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function ensureAudio() {
    if (!S.audio) {
      S.audio = new Audio();
      S.audio.preload = "auto";
      S.audio.addEventListener("ended", onAudioEnded);
    }
    return S.audio;
  }

  // ---------- Service worker ----------
  function initServiceWorker() {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }

  // ---------- Load available reading sets ----------
  async function loadReadingSetList() {
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
      opt.textContent = "Error loading reading sets";
      elSelect.appendChild(opt);
      elSelect.disabled = true;
      elDownload.disabled = true;
      elStatus.textContent = "Unable to load reading sets. Check connection.";
    }
  }

  // ---------- Load a specific reading set ----------
  async function loadReadingSet(name) {
    if (!name) return;
    stopSequence();
    clearWordHighlight();
    S.currentSet = name;
    S.passages = [];
    S.wordSpans = {};
    S.activeSeg = null;
    renderPassagesPlaceholder("Loading passage…");
    elStatus.textContent = "Loading reading set…";
    elDownload.disabled = true;

    try {
      const url = "../sets/" + encodeURIComponent(name) + ".json";
      const resp = await fetch(url, { cache: "no-cache" });
      if (!resp.ok) throw new Error("fetch failed");
      const data = await resp.json();
      const passages = (data && data.passages) || [];
      S.passages = passages;
      S.wordSpans = {};
      S.activeSeg = null;
      renderPassages();
      elStatus.textContent =
        "Loaded “" + niceName(name) + "” – " + passages.length + " lines.";
      elDownload.disabled = !passages.length;
    } catch (err) {
      console.error(err);
      S.passages = [];
      S.wordSpans = {};
      S.activeSeg = null;
      renderPassagesPlaceholder("Error loading reading set. Check connection.");
      elStatus.textContent = "Error loading reading set.";
      elDownload.disabled = true;
    }
  }

  // ---------- Rendering ----------
  function renderPassagesPlaceholder(message) {
    elPassages.classList.remove("show-en");
    elPassages.innerHTML =
      '<p style="font-size:.9rem; color:var(--muted,#5a6472); margin:0;">' +
      message +
      "</p>";
  }

  function renderPassages() {
    elPassages.innerHTML = "";
    elPassages.classList.remove("show-en");
    S.wordSpans = {};

    if (!S.passages.length) {
      renderPassagesPlaceholder(
        "No passages found in this set. Choose a different one."
      );
      return;
    }

    S.passages.forEach((p, segIndex) => {
      const block = document.createElement("div");
      block.className = "passage-block";

      if (p.title) {
        const h = document.createElement("p");
        h.className = "passage-title";
        h.textContent = p.title;
        block.appendChild(h);
      }

      const pl = document.createElement("p");
      pl.className = "passage-pl";
      pl.dataset.segIndex = String(segIndex);

      const words = String(p.polish || "").split(/\s+/).filter(Boolean);
      const spans = [];
      words.forEach((w, i) => {
        const span = document.createElement("span");
        span.className = "pl-word";
        span.dataset.segIndex = String(segIndex);
        span.dataset.wordIndex = String(i);
        span.textContent = (i === words.length - 1 ? w : w + " ");
        pl.appendChild(span);
        spans.push(span);
      });
      S.wordSpans[segIndex] = spans;

      const en = document.createElement("p");
      en.className = "passage-en";
      en.dataset.segIndex = String(segIndex);
      en.textContent = p.english || "";

      block.appendChild(pl);
      block.appendChild(en);
      elPassages.appendChild(block);
    });
  }

  // ---------- Playback sequence ----------
  function playSequenceFromStart() {
    if (!S.passages.length || !S.currentSet) return;
    stopSequence();
    S.seqIndex = 0;
    S.playingSequence = true;
    playSegment(S.seqIndex);
  }

  function playSegment(segIndex) {
    if (!S.currentSet || !S.passages.length) return;
    if (segIndex < 0 || segIndex >= S.passages.length) {
      stopSequence();
      return;
    }

    clearWordHighlight();
    S.activeSeg = segIndex;

    const audio = ensureAudio();
    audio.pause();
    audio.currentTime = 0;
    audio.playbackRate = S.playbackRate;

    const url = window.AudioPaths
      ? AudioPaths.readingPath(S.currentSet, segIndex, null)
      : null;
    if (!url) return;

    audio.src = url;

    const spans = S.wordSpans[segIndex] || [];
    const fallbackWordMs = spans.length ? 400 : 0;

    // Start highlighting once metadata is known; fall back if metadata is slow.
    audio.onloadedmetadata = () => {
      const dur = audio.duration || (spans.length * 0.4);
      startWordHighlight(segIndex, dur);
      audio.play().catch(() => {});
    };

    // Fallback in case metadata never loads
    setTimeout(() => {
      if (!audio.paused && !S.wordTimer && spans.length) {
        startWordHighlight(segIndex, (fallbackWordMs * spans.length) / 1000);
      }
    }, 1000);

    audio.play().catch(() => {});
  }

  function onAudioEnded() {
    clearWordHighlight();
    if (!S.playingSequence) return;

    S.seqIndex += 1;
    if (S.seqIndex >= S.passages.length) {
      // End of sequence
      stopSequence();
    } else {
      playSegment(S.seqIndex);
    }
  }

  function stopSequence() {
    const audio = ensureAudio();
    audio.pause();
    S.playingSequence = false;
    S.seqIndex = 0;
    clearWordHighlight();
  }

  function pausePlayback() {
    const audio = ensureAudio();
    audio.pause();
    S.playingSequence = false;
    clearWordHighlight();
  }

  function replaySequence() {
    playSequenceFromStart();
  }

  // ---------- Word highlighting ----------
  function clearWordHighlight() {
    if (S.wordTimer) {
      clearInterval(S.wordTimer);
      S.wordTimer = null;
    }
    Object.values(S.wordSpans).forEach((spans) => {
      spans.forEach((el) => el.classList.remove("active"));
    });
    S.activeSeg = null;
  }

  function startWordHighlight(segIndex, durationSeconds) {
    clearWordHighlight();
    const spans = S.wordSpans[segIndex] || [];
    if (!spans.length) return;

    const totalMs = Math.max(durationSeconds * 1000, spans.length * 150);
    const stepMs = Math.max(120, totalMs / spans.length);

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

  // ---------- Approximate pronunciation helper ----------
  function approxPron(word) {
    let w = String(word || "").toLowerCase();

    // Multi-character patterns first
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

    // Audio per passage index
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
      "Downloading audio and passage for “" +
      niceName(curSet) +
      "” in the background…";
  }

  // ---------- Click handlers ----------
  function onPassagesClick(evt) {
    const target = evt.target;
    if (!target) return;

    // If a word span: show pronunciation + play its sentence
    if (target.classList.contains("pl-word")) {
      const word = target.textContent.replace(/\s+$/, "");
      showPronForWord(word);

      const segIndex = Number(target.dataset.segIndex || "0");
      S.playingSequence = false;
      S.seqIndex = segIndex;
      playSegment(segIndex);
      return;
    }

    // If click somewhere in a Polish line: play that line
    const pl = target.closest(".passage-pl");
    if (pl && typeof pl.dataset.segIndex !== "undefined") {
      const segIndex = Number(pl.dataset.segIndex || "0");
      clearPronPanel();
      S.playingSequence = false;
      S.seqIndex = segIndex;
      playSegment(segIndex);
    }
  }

  // ---------- Event wiring ----------
  function initEvents() {
    elSelect.addEventListener("change", (e) => {
      const name = e.target.value || "";
      if (!name) return;
      loadReadingSet(name);
    });

    btnPlayAll.addEventListener("click", () => {
      playSequenceFromStart();
    });

    btnPause.addEventListener("click", () => {
      pausePlayback();
    });

    btnReplay.addEventListener("click", () => {
      replaySequence();
    });

    btnSlow.addEventListener("click", () => {
      S.playbackRate = S.playbackRate === 1.0 ? 0.8 : 1.0;
      btnSlow.textContent = S.playbackRate === 1.0 ? "0.8× Slow" : "1.0× Normal";
    });

    btnToggleEnglish.addEventListener("click", () => {
      const show = !elPassages.classList.contains("show-en");
      elPassages.classList.toggle("show-en", show);
      btnToggleEnglish.textContent = show ? "Hide English" : "Show English";
    });

    elPassages.addEventListener("click", onPassagesClick);

    elDownload.addEventListener("click", downloadReadingSetOffline);
    pronClearBtn.addEventListener("click", clearPronPanel);
  }

  // ---------- Bootstrap ----------
  window.addEventListener("DOMContentLoaded", () => {
    initServiceWorker();
    initEvents();
    loadReadingSetList();
    renderPassagesPlaceholder(
      "Choose a reading set to see the Polish text and play the audio."
    );
  });
})();
