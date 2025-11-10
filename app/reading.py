# app/reading.py

import json
from .constants import PAGES_DIR, SETS_DIR


def generate_reading_html(set_name, data=None):
    """
    Generates docs/reading/<set_name>/index.html for reading mode.

    Azure-enabled reading (continuous recognition + per-word scoring):
      - “Start Reading” uses Azure Pronunciation Assessment (word-level).
      - “Listen (Polish)” plays docs/static/<set>/reading/<idx>.mp3 or CDN via manifest.
      - Graceful fallback if token/SDK is unavailable.
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

    passages_json = json.dumps(data, ensure_ascii=False).replace(r"</", r"<\/")

    html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="../../static/brand.svg" />
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

<!-- Config + helper scripts (relative to docs/reading/<set>/index.html) -->
<script src="../../static/js/app-config.js"></script>
<script src="../../static/js/api.js"></script>
<script src="../../static/js/audio-paths.js"></script>
<!-- Azure Speech SDK -->
<script src="https://aka.ms/csspeech/jsbrowserpackageraw"></script>

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
let replayUrl = null;
let startTime = 0;
let wordsSpans = [];
let wordsMeta = []; // {{ text, idx, score }}
let r2Manifest = null; // optional CDN manifest

// ---------- Helpers ----------
function byId(id) {{ return document.getElementById(id); }}
function _norm(s) {{ return (s || "").normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").toLowerCase(); }}

async function prewarmMic() {{
  try {{
    if (!navigator.mediaDevices?.getUserMedia) return;
    const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
    stream.getTracks().forEach(tr => tr.stop());
    try {{
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (Ctx) {{
        const ctx = new Ctx();
        await ctx.resume();
        await new Promise(r => setTimeout(r, 30));
        await ctx.close();
      }}
    }} catch(_){{
    }}
  }} catch(_){{
  }}
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

  const tokens = (p.polish || "")
    .replace(/[.,!?;:()„”"'’]/g, " ")
    .split(/\\s+/).filter(Boolean);

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
  if (idx >= 0 && idx < wordsSpans.length) {{
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

// ---------- Azure token + config ----------
async function fetchToken() {{
  const c = window.__speechTok;
  if (c && c.exp > Date.now()) return c;
  const tok = await api.get('/api/speech_token', {{ noAuth: true }});
  const token  = tok && (tok.token || tok.access_token);
  const region = tok && (tok.region || tok.location || tok.regionName);
  if (!token || !region) return {{ token:null, region:null }};
  const ttlMs = Math.max(60_000, ((tok && tok.expires_in ? tok.expires_in : 540) * 1000) - 30_000);
  window.__speechTok = {{ token, region, exp: Date.now() + ttlMs }};
  return window.__speechTok;
}}

async function speechConfig() {{
  if (!window.SpeechSDK) throw new Error("sdk_not_loaded");
  const t = await fetchToken();
  if (!t.token || !t.region) throw new Error("no_token");
  const cfg = SpeechSDK.SpeechConfig.fromAuthorizationToken(t.token, t.region);
  cfg.speechRecognitionLanguage = "pl-PL";
  // Detailed JSON + word timestamps
  cfg.outputFormat = SpeechSDK.OutputFormat.Detailed;
  cfg.setProperty(SpeechSDK.PropertyId.SpeechServiceResponse_RequestDetailedResultTrueFalse, "true");
  cfg.setProperty(SpeechSDK.PropertyId.SpeechServiceResponse_RequestWordLevelTimestamps, "true");
  // Slightly forgiving silence windows for continuous mode
  cfg.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "2000");
  cfg.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "800");
  return cfg;
}}

async function setupRecognizer(referenceText) {{
  const cfg = await speechConfig();
  const audioCfg = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
  const rec = new SpeechSDK.SpeechRecognizer(cfg, audioCfg);

  if (referenceText) {{
    const pa = new SpeechSDK.PronunciationAssessmentConfig(
      referenceText,
      SpeechSDK.PronunciationAssessmentGradingSystem.HundredMark,
      SpeechSDK.PronunciationAssessmentGranularity.Word,
      true // enable miscue
    );
    pa.applyTo(rec);
  }}
  return rec;
}}

// ---------- Scoring plumbing ----------
function attachRecognitionHandlers(recognizer, passageText) {{
  startTime = Date.now();
  let nextPtr = 0;
  const maxLookahead = 4;

  function applyScoresFromJson(j) {{
    const nbest0 = j?.NBest?.[0];
    const words = nbest0?.Words || [];
    if (!words.length) {{
      const acc = Math.round(
        (nbest0?.PronunciationAssessment?.AccuracyScore) ??
        (j?.PronunciationAssessment?.AccuracyScore) ?? 0
      );
      if (acc > 0) {{
        for (let i = nextPtr; i < wordsMeta.length; i++) {{
          if (wordsMeta[i].score == null) {{
            wordsMeta[i].score = acc;
            wordsSpans[i].classList.remove("w-good","w-mid","w-bad");
            wordsSpans[i].classList.add(colorByScore(acc));
          }}
        }}
        updateStats();
      }}
      return;
    }}

    for (const w of words) {{
      const wText = _norm(w.Word || w.word || w.Display || "");
      const wScore = Math.round(w?.PronunciationAssessment?.AccuracyScore ?? 0);
      if (!wText) continue;

      let matched = -1;
      for (let k = 0; k < maxLookahead && (nextPtr + k) < wordsMeta.length; k++) {{
        const candidateIdx = nextPtr + k;
        const cand = _norm(wordsMeta[candidateIdx].text);
        if (cand === wText) {{ matched = candidateIdx; break; }}
      }}

      if (matched >= 0) {{
        while (nextPtr < matched) {{
          if (wordsMeta[nextPtr].score == null) wordsMeta[nextPtr].score = 0;
          wordsSpans[nextPtr].classList.remove("w-good","w-mid","w-bad");
          wordsSpans[nextPtr].classList.add(colorByScore(0));
          nextPtr++;
        }}
        wordsMeta[matched].score = wScore;
        wordsSpans[matched].classList.remove("w-good","w-mid","w-bad");
        wordsSpans[matched].classList.add(colorByScore(wScore));
        nextPtr = matched + 1;
      }}
    }}

    highlightWord(nextPtr);
    updateStats();
  }}

  function parseAnyResult(res) {{
    try {{
      const rawPA  = res?.result?.privPronunciationAssessmentJson || res?.privPronunciationAssessmentJson;
      const rawSTT = res?.result?.properties?.getProperty(SpeechSDK.PropertyId.SpeechServiceResponse_JsonResult);
      const raw = rawPA || rawSTT;
      if (!raw) return null;
      return JSON.parse(raw);
    }} catch (_) {{
      return null;
    }}
  }}

  recognizer.recognizing = (s, e) => {{
    byId("status").textContent = "🎙 Listening…";
    const j = parseAnyResult(e);
    if (j) applyScoresFromJson(j);
  }};

  recognizer.recognized = (s, e) => {{
    const j = parseAnyResult(e);
    if (j) applyScoresFromJson(j);
  }};

  recognizer.canceled = () => {{
    byId("status").textContent = "⚠️ Canceled";
  }};

  recognizer.sessionStarted = () => {{
    byId("status").textContent = "🎙 Session started";
  }};

  recognizer.sessionStopped = () => {{
    byId("status").textContent = "🛑 Session stopped";
    updateStats(true);
  }};
}}

// ---------- Optional local recording for replay ----------
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

// ---------- UI actions ----------
async function startReading() {{
  try {{
    const p = passages[currentIndex] || {{}};
    const referenceText = String(p.polish || "");
    if (!referenceText.trim()) {{
      byId("status").textContent = "⚠️ No passage text.";
      return;
    }}

    wordsMeta.forEach((w, i) => {{
      w.score = null;
      wordsSpans[i].classList.remove("w-good","w-mid","w-bad","active");
    }});
    highlightWord(0);
    byId("stats").textContent = "Starting…";
    byId("status").textContent = "🎙 Requesting microphone…";

    byId("btnStart").disabled = true;
    byId("btnStop").disabled = false;
    byId("btnReplay").disabled = true;

    // Pre-warm mic + prefetch token + tiny delay to align UI and capture
    await prewarmMic();
    await fetchToken().catch(()=>{{}});
    await new Promise(r => setTimeout(r, 250));

    recognizer = await setupRecognizer(referenceText);
    attachRecognitionHandlers(recognizer, referenceText);

    await new Promise((resolve, reject) => {{
      try {{ recognizer.startContinuousRecognitionAsync(resolve, reject); }}
      catch (e) {{ reject(e); }}
    }});
    startRecordingMyAudio();
  }} catch (e) {{
    console.error("startReading error", e);
    byId("status").textContent = "❌ " + (e && e.message ? e.message : String(e));
    byId("btnStart").disabled = false;
    byId("btnStop").disabled = true;
  }}
}}

async function stopReading() {{
  try {{
    byId("btnStop").disabled = true;
    if (recognizer) {{
      await new Promise((resolve) => {{
        try {{
          recognizer.stopContinuousRecognitionAsync(() => {{ resolve(); }}, () => resolve());
        }} catch (_) {{ resolve(); }}
      }});
    }}
  }} finally {{
    try {{
      const url = await stopRecordingMyAudio();
      if (url) {{
        const a = byId("replayAudio");
        a.src = url; a.load();
        byId("btnReplay").disabled = false;
      }}
    }} catch (_e) {{}}

    byId("status").textContent = "🛑 Stopped";
    updateStats(true);
    byId("btnStart").disabled = false;
  }}
}}

function listenPolish() {{
  const a = byId("ttsAudio");
  const p = passages[currentIndex] || {{}};
  const direct = p.audio_url || p.audio;
  let src = "";
  if (direct && /^https?:\\/\\//i.test(direct)) {{
    src = direct;
  }} else if (window.AudioPaths) {{
    src = AudioPaths.readingPath(setName, currentIndex, r2Manifest);
  }} else {{
    src = `../../static/${{encodeURIComponent(setName)}}/reading/${{encodeURIComponent(currentIndex)}}.mp3`;
  }}
  a.onerror = () => {{ byId("status").textContent = "🔇 Audio not found for this passage."; }};
  a.src = src; a.load();
  a.play().catch(() => {{ byId("status").textContent = "🔇 Unable to play audio."; }});
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
  byId("btnToggleEN").textContent = el.classList.contains("visible")
    ? "🇬🇧 Hide Translation" : "🇬🇧 Show Translation";
}}

// ---------- Lifecycle ----------
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
  try {{ if (window.AudioPaths) r2Manifest = await AudioPaths.fetchManifest(setName); }} catch(_e) {{ r2Manifest = null; }}
  byId("status").textContent = "🎙 Ready. Click “Start Reading” and speak clearly.";
  populateSelect();
  renderPassage(0);
  wireUI();
  // Prefetch speech token to avoid first-click latency
  fetchToken().catch(()=>{{}});
}})();

</script>
</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8")
    print(f"✅ reading page generated: {out_path}")
    return out_path
