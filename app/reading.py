# app/reading.py
from pathlib import Path
import json
from .constants import PAGES_DIR, SETS_DIR


def generate_reading_html(set_name, data=None):
    """
    Generates docs/reading/<set_name>/index.html for reading mode.

    Features:
      - Start/Stop continuous recognition with word-level scoring.
      - Per-word color highlights; WPM; status panel.
      - "Listen (Polish)" playback:
          1) Prefer CDN via R2 manifest (reading/<set>/<idx>.mp3) or direct item.audio_url
          2) Fallback to local static ../../static/<set>/reading/<idx>.mp3
          3) Fallback to Azure TTS if file not found
      - "Replay Me" of user's recording (robust, memory-leak safe).
      - Uses api.fetch('/api/token') so GH Pages works without hardcoded hosts.
      - Loads app-config.js to honor APP_CONFIG.assetsBase as a global CDN base.
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

    passages_json = json.dumps(data, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reading · {set_name}</title>
<link rel="preconnect" href="https://aka.ms">
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
<script src="https://aka.ms/csspeech/jsbrowserpackageraw"></script>
<!-- Config + API helper (relative to docs/reading/<set>/index.html) -->
<script src="../../static/js/app-config.js"></script>
<script src="../../static/js/api.js"></script>
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
const SpeechSDK = window.SpeechSDK;

let currentIndex = 0;
let recognizer = null;
let mediaRecorder = null;
let recordedChunks = [];
let replayUrl = null; // revoke old blobs to avoid leaks
let startTime = 0;
let wordsSpans = [];
let wordsMeta = []; // {{ text, idx, score }}

// R2 manifest (if present)
let r2Manifest = null; // {{ files: {{ "reading/<set>/<i>.mp3": "https://cdn..." }}, assetsBase: "https://cdn..." }}
let assetsCDNBase = (window.APP_CONFIG && (APP_CONFIG.assetsBase || APP_CONFIG.CDN_BASE || APP_CONFIG.R2_BASE)) || null;

// ---------- Helpers ----------
function byId(id) {{ return document.getElementById(id); }}

// Prefer R2 → fallback global base → fallback local static (relative)
function getReadingAudioPath(index) {{
  const key = `reading/${{setName}}/${{index}}.mp3`;
  if (r2Manifest?.files?.[key]) return r2Manifest.files[key];
  const base = r2Manifest?.assetsBase || r2Manifest?.cdn || r2Manifest?.base || assetsCDNBase;
  if (base) return String(base).replace(/\\/$/, '') + '/' + key;
  return `../../static/${{encodeURIComponent(setName)}}/reading/${{encodeURIComponent(index)}}.mp3`;
}}

async function loadR2Manifest() {{
  try {{
    let res = await fetch(`../../static/${{encodeURIComponent(setName)}}/r2_manifest.json`, {{ cache: "no-store" }});
    if (!res.ok) {{
      res = await fetch(`../../static/r2_manifest.json`, {{ cache: "no-store" }});
    }}
    if (res.ok) {{
      r2Manifest = await res.json();
      assetsCDNBase = assetsCDNBase || r2Manifest.assetsBase || r2Manifest.cdn || r2Manifest.base || null;
    }}
  }} catch(_) {{}}
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

// ---------- Azure token & TTS ----------
async function fetchToken() {{
  const res = await api.fetch('/api/token');
  if (!res.ok) throw new Error("token http " + res.status);
  return await res.json();
}}

async function speechConfig() {{
  const tk = await fetchToken();
  const cfg = SpeechSDK.SpeechConfig.fromAuthorizationToken(tk.token, tk.region);
  cfg.speechRecognitionLanguage = "pl-PL";
  // More forgiving silence windows for reading passages
  cfg.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "5000");
  cfg.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "1200");
  return cfg;
}}

async function speakPolish(text) {{
  try {{
    const tk = await fetchToken();
    const cfg = SpeechSDK.SpeechConfig.fromAuthorizationToken(tk.token, tk.region);
    cfg.speechSynthesisLanguage = "pl-PL";
    const synth = new SpeechSDK.SpeechSynthesizer(cfg);
    const a = byId("ttsAudio");
    return new Promise((resolve) => {{
      synth.speakTextAsync(text || "", result => {{
        try {{
          if (result && result.audioData) {{
            const blob = new Blob([result.audioData], {{type: "audio/wav"}});
            const url = URL.createObjectURL(blob);
            a.src = url; a.load();
            a.onended = () => {{
              URL.revokeObjectURL(url);
              resolve();
            }};
            a.play().catch(() => resolve());
          }} else {{
            resolve();
          }}
        }} finally {{
          synth.close();
        }}
      }}, err => {{
        console.warn("TTS error:", err);
        try {{ synth.close(); }} catch(_){{}}
        resolve();
      }});
    }});
  }} catch (e) {{
    console.warn("TTS fetch/config error:", e);
  }}
}}

// ---------- Recognition wiring ----------
async function setupRecognizer(referenceText) {{
  const cfg = await speechConfig();
  const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
  recognizer = new SpeechSDK.SpeechRecognizer(cfg, audioConfig);

  const pa = new SpeechSDK.PronunciationAssessmentConfig(
    referenceText,
    SpeechSDK.PronunciationAssessmentGradingSystem.HundredMark,
    SpeechSDK.PronunciationAssessmentGranularity.Word,
    true  // miscue
  );
  pa.applyTo(recognizer);
}}

function startRecordingMyAudio() {{
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

function attachRecognitionHandlers() {{
  recognizer.recognized = (s, e) => {{
    if (!e || !e.result || !e.result.json) return;
    try {{
      const j = JSON.parse(e.result.json);
      const nbest = (j.NBest && j.NBest[0]) ? j.NBest[0] : null;
      if (!nbest) return;

      const words = nbest.Words || [];
      words.forEach(w => {{
        const text = w.Word;
        const score = (w.PronunciationAssessment && w.PronunciationAssessment.AccuracyScore) || null;

        // Match next unscored token (case-insensitive; strip punctuation)
        const norm = (t) => (t||"").toLowerCase().replace(/[.,!?;:()"]/g, "");
        const matchIdx = wordsMeta.findIndex(m => m.score === null && norm(m.text) === norm(text));
        if (matchIdx !== -1) {{
          wordsMeta[matchIdx].score = score;
          const span = wordsSpans[matchIdx];
          span.classList.remove("w-good","w-mid","w-bad");
          const cls = (score>=80) ? "w-good" : (score>=60) ? "w-mid" : "w-bad";
          if (cls) span.classList.add(cls);
          highlightWord(matchIdx);
        }}
      }});

      updateStats(false);
    }} catch(err) {{
      console.warn("recognize parse error", err);
    }}
  }};

  recognizer.sessionStarted = () => {{
    byId("status").textContent = "Session started. Speak now…";
    byId("btnStart").disabled = true;
    byId("btnStop").disabled = false;
    startTime = Date.now();
    updateStats(false);
  }};

  recognizer.sessionStopped = async () => {{
    byId("status").textContent = "Session stopped.";
    byId("btnStart").disabled = false;
    byId("btnStop").disabled = true;
    const url = await stopRecordingMyAudio();
    if (url) {{
      const a = byId("replayAudio");
      a.src = url; a.load();
      byId("btnReplay").disabled = false;
    }}
    updateStats(true);
  }};

  recognizer.canceled = () => {{
    byId("status").textContent = "Canceled.";
    byId("btnStart").disabled = false;
    byId("btnStop").disabled = true;
  }};
}}

async function startReading() {{
  const p = passages[currentIndex] || {{}};
  if (!SpeechSDK) {{
    byId("status").textContent = "❌ Azure SDK not loaded.";
    return;
  }}
  await setupRecognizer(p.polish || "");
  attachRecognitionHandlers();
  await new Promise(r => setTimeout(r, 200));
  byId("status").textContent = "🎤 Speak now…";
  byId("btnReplay").disabled = true; // fresh recording
  startRecordingMyAudio();
  recognizer.startContinuousRecognitionAsync();
}}

function stopReading() {{
  try {{ if (recognizer) recognizer.stopContinuousRecognitionAsync(); }} catch(_){{}}
}}

function listenPolish() {{
  const a = byId("ttsAudio");
  const p = passages[currentIndex] || {{}};
  const direct = p.audio_url || p.audio;
  const src = (direct && /^https?:\\/\\//i.test(direct)) ? direct : getReadingAudioPath(currentIndex);
  const tryTTS = () => speakPolish(p.polish || "");
  a.onerror = tryTTS;
  a.onended = () => {{}};
  a.src = src; a.load();
  a.play().catch(tryTTS);
}}

function replayMe() {{
  const a = byId("replayAudio");
  if (!a.src) return;
  a.currentTime = 0;
  a.play().catch(()=>{});
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
  if (!SpeechSDK) {{
    byId("status").textContent = "⚠️ Azure SDK not loaded (check network).";
  }}
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
