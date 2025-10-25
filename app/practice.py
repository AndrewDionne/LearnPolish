# app/practice.py
from pathlib import Path
import json
from .sets_utils import sanitize_filename

DOCS_DIR = Path("docs")


def generate_practice_html(set_name, data):
    """
    Generates docs/practice/<set_name>/index.html and a set-scoped sw.js.

    Static-only front-end (no Azure SDK / tokens):
      - "Repeat after me" loop stays intact
      - Per-card audio playback uses docs/static/<set>/audio/<idx>_<sanitized>.mp3
      - Mic scoring is disabled; we auto-pass each attempt (small notice shown)
      - Optional offline cache UI preserved (no manifest / CDN required)
    """
    # Ensure output dir exists
    output_dir = DOCS_DIR / "practice" / set_name
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "index.html"

    # Preserve your audio filename convention for each entry
    safe_data = []
    for idx, entry in enumerate(data):
        phrase = entry.get("phrase", "")
        entry = dict(entry)  # shallow copy
        entry["audio_file"] = f"{idx}_{sanitize_filename(phrase)}.mp3"
        safe_data.append(entry)

    cards_json = json.dumps(safe_data, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{set_name} • Speak</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: #f9f9f9;
      margin: 0; padding: 1.25rem;
      text-align: center;
    }}
    h1 {{
      font-size: 1.6rem; margin: 0 0 1rem;
      position: relative;
    }}
    .home-btn {{
      position: absolute; right: 0; top: 0;
      font-size: 1.4em; background: none; border: none; cursor: pointer;
    }}
    .result {{ font-size: 1.1rem; color: #333; margin-top: 1.25rem; min-height: 2em; }}
    .flash {{
      margin: .25rem; padding: 12px 20px; font-size: 1rem;
      background-color: #2d6cdf; color: white; border: none; border-radius: 8px; cursor: pointer;
      display: inline-block;
    }}
    .flash.secondary {{ background-color: #6c757d; }}
    .flash:disabled {{ opacity: .6; cursor: default; }}
    #warmupContainer {{ display: none; margin: 1rem auto 0; width: 90%; max-width: 420px; }}
    #warmupBarWrapper {{ background:#ddd; border-radius:8px; overflow:hidden; height:20px; }}
    #warmupBar {{ background:#28a745; width:0%; height:100%; transition:width .2s; }}
    #warmupText {{ margin-top:.5rem; font-size:.9rem; color:#555; }}
  </style>
</head>
<body>
  <h1>{set_name} • Speak <button class="home-btn" onclick="goHome()">🏠</button></h1>

  <div>
    <button id="startBtn" class="flash">▶️ Start Practice</button>
    <button id="pauseBtn" class="flash secondary" style="display:none;">⏸ Pause</button>
    <button id="restartBtn" class="flash secondary" style="display:none;">🔁 Restart</button>
  </div>

  <div id="warmupContainer">
    <div id="warmupBarWrapper"><div id="warmupBar"></div></div>
    <p id="warmupText">Preparing microphone…</p>
  </div>

  <div id="result" class="result">🎙 Get ready...</div>

  <!-- Azure Speech SDK removed: using static MP3 playback only -->

  <!-- Config + API helper (relative to docs/practice/<set>/index.html) -->
  <script src="../../static/js/app-config.js"></script>
  <script src="../../static/js/api.js"></script>
  <script src="../../static/js/audio-paths.js"></script>

  <script>
    // ===== State =====
    let hasStarted = false;
    let paused = false;
    let index = 0;
    let attempts = 0;
    let isRunning = false;

    // Azure SDK explicitly disabled on front-end
    const SpeechSDK = null;
    let cachedSpeechConfig = null;
    let globalRecognizer = null;
    let isRecognizerActive = false;

    let preloadedAudio = {{}};

    // Manifest/CDN disabled
    let r2Manifest = null;
    let assetsCDNBase = null;

    const setName = "{set_name}";
    const cards = {cards_json};
    const PASS_THRESHOLD = 70;

    // Mirror of Python sanitize_filename
    function sanitizeFilename(text) {{
      return (text || "")
        .normalize("NFD").replace(/[\\u0300-\\u036f]/g, "")
        .replace(/[^a-zA-Z0-9_-]+/g, "_")
        .replace(/^_+|_+$/g, "");
    }}

    // System audio path (relative works for GH Pages and Flask)
    function getSystemAudioPath(name) {{
      return `../../static/system_audio/${{name}}.mp3`;
    }}

    // Build an audio URL for a card item (index + fields) → local static fallback
    function audioUrlFor(setName, index, item) {{
      const explicit = item?.audio_url || item?.audio;
      if (explicit && /^https?:\\/\\//i.test(explicit)) return explicit;

      const fn = (item?.audio_file && String(item.audio_file))
              || (String(index) + "_" + sanitizeFilename(item?.phrase || item?.polish || "") + ".mp3");

      // local static fallback (preferred)
      return "../../static/" + encodeURIComponent(setName) + "/audio/" + encodeURIComponent(fn);
    }}

    function preloadAudioFiles() {{
      preloadedAudio = {{}};
      for (let i = 0; i < cards.length; i++) {{
        const item = cards[i] || {{}};
        const url = audioUrlFor(setName, i, item);
        preloadedAudio[i] = new Audio(url);
      }}
    }}

    function playAudioByIndex(i, callback) {{
      const a = preloadedAudio[i];
      if (!a) {{ console.warn("⚠️ Audio not preloaded for index", i); callback(); return; }}
      a.currentTime = 0;
      a.onended = callback;
      a.onerror = () => {{ console.warn("⚠️ Audio failed @", i); callback(); }};
      const p = a.play();
      if (p) p.catch(err => {{ console.warn("🔇 Autoplay blocked:", err); callback(); }});
    }}

    function playSystemAudio(name, callback) {{
      const audio = new Audio(getSystemAudioPath(name));
      audio.onended = callback;
      audio.onerror = () => {{ console.warn("⚠️ Failed system audio:", name); callback(); }};
      const p = audio.play();
      if (p) p.catch(err => {{ console.warn("🔇 Autoplay blocked:", err); callback(); }});
    }}

    // Manifest disabled: local static only
    async function loadR2Manifest() {{
      r2Manifest = null;
      assetsCDNBase = null;
    }}

    // ===== Azure Speech stubs (disabled) =====
    async function getSpeechConfig() {{
      throw new Error("Speech disabled");
    }}

    async function initRecognizer() {{
      // never called with speech disabled; keep stub for compatibility
      return null;
    }}

    async function warmupMic() {{
      // simple progress animation to keep UI behavior consistent
      const container = document.getElementById("warmupContainer");
      const bar = document.getElementById("warmupBar");
      const text = document.getElementById("warmupText");

      container.style.display = "block";
      bar.style.width = "0%";
      text.textContent = "Preparing… (mic scoring disabled)";

      let progress = 0;
      const interval = setInterval(() => {{
        progress += 10; bar.style.width = progress + "%";
        if (progress >= 100) {{
          clearInterval(interval);
          text.textContent = "Ready!";
          setTimeout(() => container.style.display = "none", 400);
        }}
      }}, 60);
    }}

    // Return an auto-pass score and show a small notice; keeps flow smooth
    async function assessPronunciation(phrase, isFirst=false) {{
      const resultDiv = document.getElementById("result");
      resultDiv.innerHTML = `🎤 Say: <strong>${{phrase}}</strong><br><span style="font-size:.95em;opacity:.8;">(Mic scoring disabled — auto-pass)</span>`;
      // brief pause to feel responsive
      await new Promise(r => setTimeout(r, isFirst ? 800 : 400));
      playSystemAudio("good", () => {{}});
      return PASS_THRESHOLD;
    }}

    async function runPractice() {{
      if (paused || isRunning) return;
      if (index >= cards.length) {{
        document.getElementById("result").innerHTML = "✅ Done!";
        return;
      }}

      isRunning = true;

      // 1) Play Polish audio
      await new Promise(resolve => playAudioByIndex(index, resolve));
      if (paused) {{ isRunning = false; return; }}

      // 2) (Disabled) Assess pronunciation → auto-pass keeps loop moving
      const phrase = (cards[index] || {{}}).phrase || "";
      const score = await assessPronunciation(phrase, index === 0);
      if (paused) {{ isRunning = false; return; }}

      // 3) Decide next (auto-pass always advances)
      if (score >= PASS_THRESHOLD || attempts >= 2) {{
        index++; attempts = 0;
      }} else {{
        attempts++;
        const r = document.getElementById("result");
        r.innerHTML += "<br>🔁 Try again!";
      }}

      isRunning = false;
      setTimeout(() => {{ if (!paused) runPractice(); }}, 800);
    }}

    // ---------- Offline helpers ----------
    let swReg = null;
    function allAudioUrls() {{
      const urls = [];
      for (let i = 0; i < cards.length; i++) {{
        urls.push(audioUrlFor(setName, i, cards[i] || {{}}));
      }}
      ["repeat_after_me","good","try_again"].forEach(n => urls.push(getSystemAudioPath(n)));
      return Array.from(new Set(urls));
    }}
    async function ensureSW() {{
      if (!("serviceWorker" in navigator)) return null;
      try {{
        swReg = await navigator.serviceWorker.register("./sw.js", {{ scope: "./" }});
        await navigator.serviceWorker.ready;
        return swReg;
      }} catch (e) {{
        console.log("SW register failed", e);
        return null;
      }}
    }}

    // ===== Startup =====
    document.addEventListener("DOMContentLoaded", async () => {{
      const startBtn = document.getElementById("startBtn");
      const pauseBtn = document.getElementById("pauseBtn");
      const restartBtn = document.getElementById("restartBtn");

      // Inject Offline UI
      const firstControls = document.querySelector("h1 + div");
      const offWrap = document.createElement("div");
      offWrap.style.marginTop = ".5rem";
      offWrap.innerHTML = `
        <button id="offlineBtn" class="flash secondary" disabled>⬇️ Offline</button>
        <button id="offlineRemoveBtn" class="flash secondary" style="display:none;">🗑 Remove</button>
        <span id="offlineStatus" class="result" style="display:block;margin-top:.5rem;"></span>
      `;
      firstControls.after(offWrap);
      const offlineBtn = document.getElementById("offlineBtn");
      const offlineRemoveBtn = document.getElementById("offlineRemoveBtn");
      const offlineStatus = document.getElementById("offlineStatus");

      // Manifest disabled; still call to keep same flow
      await loadR2Manifest();

      // Preload audio (local static)
      preloadAudioFiles();

      // Warm up (visual only)
      await warmupMic();

      // Offline SW wiring
      await ensureSW();
      if (!swReg) {{
        offlineStatus.textContent = "⚠️ Offline not supported in this browser.";
      }}
      navigator.serviceWorker?.addEventListener("message", (ev) => {{
        const d = ev.data || {{}};
        if (d.type === "CACHE_PROGRESS") {{
          offlineStatus.textContent = `⬇️ ${{d.done}} / ${{d.total}} files cached…`;
        }} else if (d.type === "CACHE_DONE") {{
          offlineStatus.textContent = "✅ Available offline";
          offlineRemoveBtn.style.display = "inline-block";
        }} else if (d.type === "UNCACHE_DONE") {{
          offlineStatus.textContent = "🗑 Removed offline copy";
          offlineRemoveBtn.style.display = "none";
        }} else if (d.type === "CACHE_ERROR") {{
          offlineStatus.textContent = "❌ Offline failed: " + (d.error || "");
        }}
      }});
      offlineBtn.addEventListener("click", async () => {{
        const reg = await ensureSW();
        if (!reg || !reg.active) {{
          offlineStatus.textContent = "❌ Offline not available.";
          return;
        }}
        offlineStatus.textContent = "⬇️ Downloading…";
        const urls = allAudioUrls();
        reg.active.postMessage({{ type: "CACHE_SET", cache: `practice-{set_name}`, urls }});
      }});
      offlineRemoveBtn.addEventListener("click", async () => {{
        const reg = await ensureSW();
        if (!reg || !reg.active) return;
        reg.active.postMessage({{ type: "UNCACHE_SET", cache: `practice-{set_name}` }});
      }});

      // Start/Pause/Restart
      startBtn.addEventListener("click", () => {{
        if (!hasStarted) {{
          hasStarted = true; paused = false;
          startBtn.style.display = "none";
          pauseBtn.style.display = "inline-block";
          restartBtn.style.display = "inline-block";
          playSystemAudio("repeat_after_me", () => runPractice());
        }}
      }});
      pauseBtn.addEventListener("click", () => {{
        if (!hasStarted) return;
        paused = !paused;
        pauseBtn.textContent = paused ? "▶️ Resume" : "⏸ Pause";
        if (!paused && !isRunning) {{
          playSystemAudio("repeat_after_me", () => runPractice());
        }}
      }});
      restartBtn.addEventListener("click", () => {{
        paused = false;
        index = 0; attempts = 0; isRunning = false;
        pauseBtn.textContent = "⏸ Pause";
        playSystemAudio("repeat_after_me", () => runPractice());
      }});
    }});

    function goHome() {{ window.location.href = "../../index.html"; }}
  </script>
</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8")

    # Service worker (unchanged)
    sw_js = """/* practice SW */
self.addEventListener('install', (e) => { self.skipWaiting(); });
self.addEventListener('activate', (e) => { self.clients.claim(); });

function isValid(u){ try { new URL(u); return true; } catch(_) { return false; } }

self.addEventListener('message', async (e) => {
  const data = e.data || {};
  const client = await self.clients.get(e.source && e.source.id);
  if (data.type === 'CACHE_SET') {
    const cacheName = data.cache || 'practice-cache';
    const urls = Array.isArray(data.urls) ? data.urls.filter(isValid) : [];
    try {
      const cache = await caches.open(cacheName);
      let done = 0, total = urls.length;
      for (const u of urls) {
        try {
          const res = await fetch(u, { mode: 'cors' });
          if (res.ok || res.type === 'opaque') {
            await cache.put(u, res);
          }
        } catch (_) { /* skip failed */ }
        done++;
        client && client.postMessage({ type: 'CACHE_PROGRESS', done, total });
      }
      client && client.postMessage({ type: 'CACHE_DONE', cache: cacheName });
    } catch (err) {
      client && client.postMessage({ type: 'CACHE_ERROR', error: String(err) });
    }
  } else if (data.type === 'UNCACHE_SET') {
    const cacheName = data.cache || 'practice-cache';
    await caches.delete(cacheName);
    client && client.postMessage({ type: 'UNCACHE_DONE', cache: cacheName });
  }
});

// Cache-first for anything we have; otherwise fall through to network
self.addEventListener('fetch', (event) => {
  event.respondWith((async () => {
    const reqUrl = event.request.url;
    const names = await caches.keys();
    for (const name of names) {
      const cache = await caches.open(name);
      const hit = await cache.match(reqUrl, { ignoreSearch: true });
      if (hit) return hit;
    }
    try { return await fetch(event.request); } catch (_) { return new Response('', { status: 504 }); }
  })());
});
"""
    (output_dir / "sw.js").write_text(sw_js, encoding="utf-8")

    print(f"✅ practice page generated: {out_path}")
    return out_path
