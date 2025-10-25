# app/reading.py
from pathlib import Path
import json
from .constants import PAGES_DIR, SETS_DIR


def generate_reading_html(set_name, data=None):
    """
    Generates docs/reading/<set_name>/index.html for reading mode.

    Static-only behavior (no Azure on front-end):
      - "Listen (Polish)" plays docs/static/<set>/reading/<idx>.mp3
      - No manifest lookups; no token calls; no mic/recognition
      - Gentle notice if an audio file is missing
    """
    out_dir = PAGES_DIR / "reading" / set_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.html"

    # Load set data if not provided
    if data is None:
        sets_file = SETS_DIR / f"{set_name}.json"
        if not sets_file.exists():
            raise FileNotFoundError(f"No set JSON for reading: {sets_file}")
        data = json.loads(sets_file.read_text(encoding="utf-8"))

    passages_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

    html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reading · {set_name}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, system-ui, sans-serif; margin: 24px; max-width: 900px; }}
  .toolbar {{ display:flex; gap:8px; flex-wrap: wrap; align-items:center; margin-bottom: 12px; }}
  button {{ padding:8px 12px; border-radius: 10px; border:0; background:#007bff; color:#fff; cursor:pointer; }}
  button.secondary {{ background:#6c757d; }}
  button:disabled {{ opacity:.6; cursor:default; }}
  .passage {{ font-size: 1.35rem; line-height: 1.8; margin: 16px 0; }}
  .word {{ padding: 2px 4px; border-radius: 6px; margin: 0 1px; display:inline-block; }}
  .word.active {{ outline: 2px solid #007bff; }}
  .w-good {{ background: rgba(0,180,0,.12); }}
  .w-mid  {{ background: rgba(255,165,0,.15); }}
  .w-bad  {{ background: rgba(255,0,0,.12); }}
  .meta {{ color:#666; font-size: .9rem; }}
  .stats {{ margin-top: 12px; padding: 10px; border: 1px solid #eee; border-radius: 10px; background:#fafafa; }}
  .translation {{ margin-top: 12px; color:#333; display:none; }}
  .translation.visible {{ display:block; }}
  .row {{ display:flex; align-items:center; gap:8px; flex-wrap: wrap; }}
  select {{ padding:6px; border-radius:8px; }}
  audio {{ display:none; }}
  a.home {{ position:absolute; right:16px; top:16px; text-decoration:none; background:#007bff; color:#fff; padding:6px 10px; border-radius:8px; }}
</style>
<!-- Azure Speech SDK removed: using static MP3 playback only -->

<!-- Config + helper scripts (relative to docs/reading/<set>/index.html) -->
<script src="../../static/js/app-config.js"></script>
<script src="../../static/js/api.js"></script>
<script src="../../static/js/audio-paths.js"></script>

</head>
<body>
  <a class="home" href="#" onclick="goHome(); return false;">🏠 Home</a>

  <h1>Reading · {set_name}</h1>

  <div class="toolbar">
    <div class="row">
      <label for="passageSelect"><strong>Passage:</strong></label>
      <select id="passageSelect"></select>
    </div>
    <button id="btnStart">🎤 Start Reading</button>
    <button id="btnStop" class="secondary" disabled>⏹ Stop</button>
    <button id="btnListen" class="secondary">🔊 Listen (Polish)</button>
    <button id="btnReplay" class="secondary" disabled>🎧 Replay Me</button>
    <button id="btnToggleEN" class="secondary">🇬🇧 Show Translation</button>
  </div>

  <div id="title" class="meta"></div>
  <div id="passage" class="passage"></div>
  <div id="translation" class="translation"></div>
  <div id="stats" class="stats">Ready.</div>
  <div id="status" class="meta"></div>

  <!-- Hidden audios -->
  <audio id="ttsAudio"></audio>
  <audio id="replayAudio"></audio>

<script>
const passages = {passages_json};
const setName = "{set_name}";

// Recognition fully disabled on front-end
const SpeechSDK = null;

let currentIndex = 0;
let recognizer = null;
let mediaRecorder = null;
let recordedChunks = [];
let replayUrl = null; // revoke old blobs to avoid leaks
let startTime = 0;
let wordsSpans = [];
let wordsMeta = []; // {{ text, idx, score }}

// Manifest disabled (local static only)
let r2Manifest = null;
let assetsCDNBase = null;

// ---------- Helpers ----------
function byId(id) {{ return document.getElementById(id); }}

// Local static path: docs/static/<set>/reading/<index>.mp3
function getReadingAudioPath(index) {{
  return `../../static/${{encodeURIComponent(setName)}}/reading/${{encodeURIComponent(index)}}.mp3`;
}}

async function loadR2Manifest() {{
  // No manifest/CDN: use local static files only.
  r2Manifest = null;
  assetsCDNBase = null;
}}

function populateSelect() {{
  const sel = byId("passageSelect");
  sel.innerHTML = "";
  passages.forEach((p, i) => {{
    const opt = document.createElement("option");
    opt.value = i;
    opt.textContent = p.title || ("Passage " + (i+1));
    sel.appendChild(opt);
  }});
  sel.value = "0";
}}

function renderPassage(i) {{
  const p = passages[i] || {{}};
  byId("title").textContent = p.title || "";
  byId("translation").textContent = p.english || "";
  const container = byId("passage");
  container.innerHTML = "";
  wordsSpans = [];
  wordsMeta = [];

  const tokens = (p.polish || "").split(/\\s+/).filter(Boolean);
  tokens.forEach((w, idx) => {{
    const span = document.createElement("span");
    span.className = "word";
    span.dataset.idx = String(idx);
    span.textContent = w;
    container.appendChild(span);
    wordsSpans.push(span);
    wordsMeta.push({{ text: w, idx, score: null }});
    container.appendChild(document.createTextNode(" "));
  }});
  byId("stats").textContent = "Ready.";
  byId("status").textContent = "";
  byId("btnReplay").disabled = true;
}}

function colorByScore(s) {{
  if (s === null || isNaN(s)) return "";
  if (s >= 80) return "w-good";
  if (s >= 60) return "w-mid";
  return "w-bad";
}}

function highlightWord(idx, cls="active") {{
  wordsSpans.forEach(s => s.classList.remove("active"));
  if (idx >=0 && idx < wordsSpans.length) {{
    wordsSpans[idx].classList.add(cls);
    wordsSpans[idx].scrollIntoView({{ block:"center", inline:"nearest", behavior:"smooth" }});
  }}
}}

function computeWPM(elapsedMs, wordsCount) {{
  if (elapsedMs <= 0) return 0;
  return Math.round((wordsCount / (elapsedMs/1000)) * 60);
}}

function updateStats(final=false) {{
  const done = wordsMeta.filter(w => typeof w.score === "number");
  const avg = done.length ? (done.reduce((a,b)=>a+b.score,0) / done.length) : 0;
  const elapsed = Date.now() - startTime;
  const wpm = computeWPM(elapsed, done.length);
  const status = final ? "Finished" : "Listening…";
  byId("stats").innerHTML = `
    <div><strong>Status:</strong> ${{status}}</div>
    <div><strong>Pronunciation (avg of scored words):</strong> ${{avg.toFixed(1)}}%</div>
    <div><strong>Words recognized:</strong> ${{done.length}} / ${{wordsMeta.length}}</div>
    <div><strong>WPM:</strong> ${{wpm}}</div>
  `;
}}

// ---- Speech-related functions are stubs (disabled) ----
async function fetchToken() {{ throw new Error("Speech disabled"); }}
async function speechConfig() {{ throw new Error("Speech disabled"); }}
async function speakPolish(_text) {{ /* disabled */ return; }}
async function setupRecognizer(_referenceText) {{ /* disabled */ return; }}
function attachRecognitionHandlers() {{ /* disabled */ return; }}

function startRecordingMyAudio() {{
  // Optional: allow user to record & replay their voice (no scoring)
  recordedChunks = [];
  navigator.mediaDevices.getUserMedia({{ audio: true }}).then(stream => {{
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = e => {{ if (e.data.size > 0) recordedChunks.push(e.data); }};
    mediaRecorder.start();
  }}).catch(() => {{}});
}}

function stopRecordingMyAudio() {{
  return new Promise(resolve => {{
    if (!mediaRecorder) return resolve(null);
    mediaRecorder.onstop = () => {{
      try {{ if (replayUrl) URL.revokeObjectURL(replayUrl); }} catch(_){{}}
      const blob = new Blob(recordedChunks, {{ type: "audio/webm" }});
      replayUrl = URL.createObjectURL(blob);
      resolve(replayUrl);
    }};
    try {{ mediaRecorder.stop(); }} catch(e) {{ resolve(null); }}
  }});
}}

async function startReading() {{
  // Mic assessment disabled; no recognizer session
  byId("status").textContent = "🔇 Reading assessment is temporarily disabled.";
  const btn = byId("btnReplay");
  if (btn) btn.disabled = true; // no recording is made automatically
  return;
}}

function stopReading() {{
  // No recognizer to stop; keep graceful try/catch
  try {{ if (recognizer) recognizer.stopContinuousRecognitionAsync(); }} catch(_){{}}
}}

function listenPolish() {{
  const a = byId("ttsAudio");
  const p = passages[currentIndex] || {{}};
  const direct = p.audio_url || p.audio;
  const src = (direct && /^https?:\\/\\//i.test(direct)) ? direct : getReadingAudioPath(currentIndex);
  a.onerror = () => {{
    byId("status").textContent = "🔇 Audio not found for this passage.";
  }};
  a.onended = () => {{}};
  a.src = src; a.load();
  a.play().catch(() => {{
    byId("status").textContent = "🔇 Unable to play audio.";
  }});
}}

function replayMe() {{
  const a = byId("replayAudio");
  if (!a.src) return;
  a.currentTime = 0;
  a.play().catch(()=>{{}});
}}

function toggleEN() {{
  const el = byId("translation");
  el.classList.toggle("visible");
  byId("btnToggleEN").textContent = el.classList.contains("visible") ? "🇬🇧 Hide Translation" : "🇬🇧 Show Translation";
}}

// ---------- UI / lifecycle ----------
function wireUI() {{
  byId("passageSelect").addEventListener("change", (e) => {{
    currentIndex = parseInt(e.target.value, 10) || 0;
    renderPassage(currentIndex);
  }});
  byId("btnStart").addEventListener("click", startReading);
  byId("btnStop").addEventListener("click", stopReading);
  byId("btnListen").addEventListener("click", listenPolish);
  byId("btnReplay").addEventListener("click", replayMe);
  byId("btnToggleEN").addEventListener("click", toggleEN);

  window.addEventListener("beforeunload", () => {{
    try {{ if (recognizer) recognizer.stopContinuousRecognitionAsync(); }} catch(_){{}}
    try {{ if (replayUrl) URL.revokeObjectURL(replayUrl); }} catch(_){{}}
  }});
  document.addEventListener("visibilitychange", () => {{
    if (document.hidden) {{
      try {{ if (recognizer) recognizer.stopContinuousRecognitionAsync(); }} catch(_){{}}
    }}
  }});
}}

function goHome() {{ window.location.href = "../../index.html"; }}

(async function init() {{
  byId("status").textContent = "ℹ️ Static audio playback only (mic scoring disabled).";
  await loadR2Manifest();
  populateSelect();
  renderPassage(0);
  wireUI();
}})();
</script>
</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8")
    print(f"✅ reading page generated: {out_path}")
    return out_path
