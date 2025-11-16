# app/reading.py
import json
from .constants import PAGES_DIR, SETS_DIR

def generate_reading_html(set_name, data=None):
    """
    Generates:
      - docs/reading/<set_name>/index.html
      - docs/reading/<set_name>/sw.js (offline audio cache)

    Features:
      • Azure continuous recognition + Pronunciation Assessment (Word granularity, miscues on)
      • Per-word colouring (good/mid/bad) with lookahead alignment and live progress
      • Token/region caching to trim first-click latency
      • "Listen (Polish)" plays reading audio (local or CDN via manifest)
      • Optional local mic recording for “Replay Me”
      • Optional offline caching of reading audio (service worker)
      • UI consistent with Path to POLISH header / bottom nav
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
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />

  <!-- Dual-host <base>: GitHub Pages vs Flask -->
  <script>
    (function () {{
      var isGH = /\\.github\\.io$/i.test(location.hostname);
      var baseHref = isGH ? '/LearnPolish/' : '/';
      document.write('<base href="' + baseHref + '">');
    }})();
  </script>

  <title>Reading • {set_name} • Path to POLISH</title>
  <link rel="stylesheet" href="static/app.css?v=5" />
  <link rel="icon" type="image/svg+xml" href="../../static/brand.svg" />

  <style>
    .wrap{{ max-width:900px; margin:0 auto 92px; padding:0 16px; }}
    .stack{{ display:grid; gap:16px }}
    .row{{ display:flex; align-items:center; gap:10px; flex-wrap:wrap }}
    .card{{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:16px }}
    .title{{ font-weight:800; font-size:18px }}

    .toolbar .btn{{ display:inline-flex; align-items:center; gap:8px; padding:10px 14px; border-radius:10px;
      border:1px solid var(--border); background:var(--card); cursor:pointer }}
    .btn-primary{{ background:var(--brand); border-color:var(--brand); color:#fff }}
    .btn:disabled{{ opacity:.6; cursor:default }}

    .passage{{ font-size:1.25rem; line-height:1.9; margin-top:8px }}
    .word{{ display:inline-block; margin:0 1px; padding:2px 4px; border-radius:6px }}
    .word.active{{ outline:2px solid var(--brand); outline-offset:2px }}
    .w-good{{ background: rgba(16,180,0,.14); }}
    .w-mid {{ background: rgba(255,165,0,.16); }}
    .w-bad {{ background: rgba(255,0,0,.14); }}

    .meta{{ color:var(--muted); font-size:.95rem }}
    .stats{{ margin-top:10px; border:1px solid var(--border); border-radius:10px; padding:10px; background:var(--card) }}

    select{{ padding:8px 10px; border-radius:10px; border:1px solid var(--border); background:var(--card) }}

    /* Debug overlay (toggle via ?debug=1) */
    #dbg{{ display:none; position:fixed; bottom:8px; left:8px; right:8px; max-height:44vh; overflow:auto;
      background:#000; color:#0f0; padding:8px 10px; border-radius:10px; font-family:ui-monospace, Menlo, monospace;
      font-size:12px; white-space:pre-wrap; z-index:9999 }}
  </style>
</head>

<body
  data-header="Path to Polish"
  data-note-lead="Reading"
  data-note-tail="{set_name}"
  style="--logo-size:40px; --banner-size:24px; --banner-size-lg:30px">

  <!-- Header -->
  <header class="topbar no-nav">
    <div class="row container">
      <div class="header-left">
        <a class="brand" href="index.html" aria-label="Path to Polish — Home">
          <svg class="brand-mark" aria-hidden="true" focusable="false">
            <use href="static/brand.svg#ptp-mark"></use>
          </svg>
          <span id="headerBanner" class="header-banner"></span>
        </a>
      </div>
      <nav class="head-actions">
        <a href="profile.html"  id="profileBtn">Profile</a>
        <a href="login.html"    id="loginLink">Sign In</a>
        <a href="register.html" id="registerLink">Register</a>
        <button id="logoutBtn" style="display:none;">Logout</button>
      </nav>
    </div>
  </header>

  <main class="wrap stack">
    <section class="card">
      <div class="row toolbar">
        <div class="row">
          <label for="passageSelect"><strong>Passage:</strong></label>
          <select id="passageSelect"></select>
        </div>
        <button id="btnStart" class="btn btn-primary">🎤 Start Reading</button>
        <button id="btnStop" class="btn" disabled>⏹ Stop</button>
        <button id="btnListen" class="btn">🔊 Listen (Polish)</button>
        <button id="btnSpeed" class="btn">🐢 0.8×</button>
        <button id="btnReplay" class="btn" disabled>🎧 Replay Me</button>
        <button id="btnToggleEN" class="btn">🇬🇧 Show Translation</button>
        <button id="btnOffline" class="btn">⬇️ Offline</button>
        <button id="btnOfflineRm" class="btn" style="display:none;">🗑 Remove</button>
        <button id="btnFinish" class="btn">✅ Finish</button>
      </div>

      <div id="title" class="meta"></div>
      <div id="passage" class="passage"></div>
      <div id="translation" class="meta" style="display:none; margin-top:8px"></div>

      <div id="stats" class="stats">Ready.</div>
      <div id="status" class="meta" style="margin-top:8px"></div>
      <div id="offlineStatus" class="meta" style="margin-top:8px"></div>

      <!-- Hidden audio tags -->
      <audio id="ttsAudio"></audio>
      <audio id="replayAudio"></audio>
    </section>
  </main>

  <div id="dbg"></div>

  <!-- Bottom nav -->
  <nav class="bottom" aria-label="Primary">
    <a href="index.html">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M3 10.5L12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1v-10.5Z" stroke-width="1.5"/></svg>
      <span>Home</span>
    </a>
    <a href="learn.html" class="active" aria-current="page">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M4 6h16M4 12h16M4 18h9" stroke-width="1.5" stroke-linecap="round"/></svg>
      <span>Learn</span>
    </a>
    <a href="manage_sets/index.html">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="4" width="18" height="16" rx="2" ry="2" stroke-width="1.5"/><path d="M7 8h10M7 12h10M7 16h7" stroke-width="1.5" stroke-linecap="round"/></svg>
      <span>Library</span>
    </a>
    <a href="dashboard.html">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M4 14h6V4H4v10Zm10 6h6V4h-6v16Z" stroke-width="1.5"/></svg>
      <span>Dashboard</span>
    </a>
    <a href="groups.html">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 12a5 5 0 1 0-5-5 5 5 0 0 0 5 5Zm-9 9a9 9 0 0 1 18 0" stroke-width="1.5" stroke-linecap="round"/></svg>
      <span>Groups</span>
    </a>
  </nav>

  <!-- Scripts -->
  <script src="static/js/app-config.js"></script>
  <script src="static/js/api.js"></script>
  <script src="static/js/page-chrome.js" defer></script>
  <script src="static/js/audio-paths.js"></script>
  <script src="static/js/results.js"></script>
  <script src="https://aka.ms/csspeech/jsbrowserpackageraw"></script>

  <script>
    const passages = {passages_json};
    const setName  = "{set_name}";
    const SpeechSDK = window.SpeechSDK;

    const DEBUG = new URL(location.href).searchParams.get('debug') === '1';
    const dbgEl = document.getElementById('dbg');
    if (DEBUG) dbgEl.style.display = 'block';
    function dbg(...a){{ if (!DEBUG) return; const d=document.createElement('div'); d.textContent=a.map(x=>typeof x==='string'?x:JSON.stringify(x)).join(' '); dbgEl.appendChild(d); dbgEl.scrollTop=dbgEl.scrollHeight; }}
    
    let currentIndex = 0;
        let recognizer = null;
    let recording = null; // MediaRecorder
    let chunks = [];
    let replayUrl = null;
    let startTime = 0;
    let isReading = false;
    let wordsSpans = [];
    let wordsMeta  = []; // {{ text, idx, score }}
    let r2Manifest = null;
    let playbackRate = 0.8; // default slow playback for Polish audio


    // ----- Helpers -----
    function byId(id){{ return document.getElementById(id); }}
    function _norm(s){{
      return (s||"").normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase().replace(/[-–—]/g,'');
    }}

    async function prewarmMic(){{
      try {{
        const m = await navigator.mediaDevices.getUserMedia({{ audio:true }});
        m.getTracks().forEach(t=>t.stop());
      }} catch(_){{
      }}
    }}

    function populateSelect(){{
      const sel = byId('passageSelect'); sel.innerHTML = '';
      passages.forEach((p,i)=>{{
        const o = document.createElement('option');
        o.value = i; o.textContent = p.title || ('Passage ' + (i+1));
        sel.appendChild(o);
      }});
      sel.value = '0';
    }}

    function renderPassage(i){{
      const p = passages[i] || {{}};
      byId('title').textContent = p.title || '';
      byId('translation').textContent = p.english || '';
      const cont = byId('passage'); cont.innerHTML = '';
      wordsSpans = []; wordsMeta = [];

      const tokens = String(p.polish||'')
        .replace(/[.,!?;:()«»„”"’'\\[\\]{{}}]/g, ' ')
        .split(/\\s+/).filter(Boolean);

      tokens.forEach((w, idx)=>{{
        const span = document.createElement('span');
        span.className = 'word'; span.dataset.idx = String(idx);
        span.textContent = w; cont.appendChild(span);
        wordsSpans.push(span); wordsMeta.push({{ text:w, idx, score:null }});
        cont.appendChild(document.createTextNode(' '));
      }});
      highlightWord(0);
      byId('stats').textContent = 'Ready.';
      byId('status').textContent = '';
      byId('btnReplay').disabled = true;
    }}

    function colorByScore(s){{
      if (s==null || isNaN(s)) return '';
      if (s >= 80) return 'w-good';
      if (s >= 60) return 'w-mid';
      return 'w-bad';
    }}

    function highlightWord(idx){{
      wordsSpans.forEach(s=>s.classList.remove('active'));
      if (idx>=0 && idx<wordsSpans.length) wordsSpans[idx].classList.add('active');
    }}

    function syncTtsProgress(){{
      const a = byId('ttsAudio');
      if (!a || !a.duration || !wordsMeta.length) return;
      const frac = a.currentTime / a.duration;
      const idx = Math.min(wordsMeta.length - 1, Math.floor(frac * wordsMeta.length));
      highlightWord(idx);
    }}

    function computeWPM(ms, words){{
      if (ms<=0) return 0; return Math.round((words/(ms/1000))*60);
    }}

    function updateStats(final=false){{
      const done = wordsMeta.filter(w=>typeof w.score==='number');
      const avg = done.length ? (done.reduce((a,b)=>a+b.score,0)/done.length) : 0;
      const elapsed = Date.now()-startTime;
      const wpm = computeWPM(elapsed, done.length);
      const status = final ? 'Finished' : 'Listening…';
      byId('stats').innerHTML = `
        <div><strong>Status:</strong> ${{status}}</div>
        <div><strong>Pronunciation (avg):</strong> ${{avg.toFixed(1)}}%</div>
        <div><strong>Words recognized:</strong> ${{done.length}} / ${{wordsMeta.length}}</div>
        <div><strong>WPM:</strong> ${{wpm}}</div>
      `;
    }}

    // ----- Token cache -----
    async function fetchToken(){{
      const c = window.__speechTok;
      if (c && c.exp > Date.now()) return c;
      const tok = await api.get('/api/speech_token', {{ noAuth:true }});
      const token  = tok && (tok.token || tok.access_token);
      const region = tok && (tok.region || tok.location || tok.regionName);
      if (!token || !region) return {{ token:null, region:null, exp:0 }};
      const ttl = Math.max(60_000, ((tok.expires_in ? tok.expires_in : 540)*1000) - 30_000);
      const out = {{ token, region, exp: Date.now()+ttl }};
      window.__speechTok = out;
      return out;
    }}

    async function speechConfig(){{
      if (!window.SpeechSDK) throw new Error('sdk_not_loaded');
      const t = await fetchToken();
      if (!t.token || !t.region) throw new Error('no_token');
      const cfg = SpeechSDK.SpeechConfig.fromAuthorizationToken(t.token, t.region);
      cfg.speechRecognitionLanguage = 'pl-PL';
      cfg.outputFormat = SpeechSDK.OutputFormat.Detailed;
      cfg.setProperty(SpeechSDK.PropertyId.SpeechServiceResponse_RequestDetailedResultTrueFalse, 'true');
      cfg.setProperty(SpeechSDK.PropertyId.SpeechServiceResponse_RequestWordLevelTimestamps, 'true');
      cfg.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, '2000');
      cfg.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, '800');
      return cfg;
    }}

    async function makeRecognizer(referenceText){{
      const cfg = await speechConfig();
      const audioCfg = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
      const rec = new SpeechSDK.SpeechRecognizer(cfg, audioCfg);
      if (referenceText){{
        const pa = new SpeechSDK.PronunciationAssessmentConfig(
          referenceText,
          SpeechSDK.PronunciationAssessmentGradingSystem.HundredMark,
          SpeechSDK.PronunciationAssessmentGranularity.Word,
          true
        );
        pa.applyTo(rec);
        try {{ SpeechSDK.PhraseListGrammar.fromRecognizer(rec)?.add(referenceText); }} catch(_){{
        }}
      }}
      return rec;
    }}

    // ----- Aligning & scoring -----
    function attachHandlers(rec, reference){{
      const wordsNorm = wordsMeta.map(w=>_norm(w.text));
      let nextPtr = 0; const LOOKAHEAD = 4;

      function applyFromJson(j){{
        if (!isReading) return;
        const nb = j?.NBest?.[0];
        const words = nb?.Words || [];
        if (!words.length) return;
        for (const w of words){{
          const wt = _norm(w.Word || w.word || w.Display || '');
          const sc = Math.round(w?.PronunciationAssessment?.AccuracyScore ?? 0);
          if (!wt) continue;
          let match=-1;
          for (let k=0;k<LOOKAHEAD && (nextPtr+k)<wordsNorm.length;k++) {{
            if (wordsNorm[nextPtr+k] === wt) {{ match = nextPtr+k; break; }}
          }}
          if (match>=0){{
            while(nextPtr<match){{
              if (wordsMeta[nextPtr].score==null) wordsMeta[nextPtr].score = 0;
              wordsSpans[nextPtr].classList.remove('w-good','w-mid','w-bad');
              wordsSpans[nextPtr].classList.add(colorByScore(0));
              nextPtr++;
            }}
            wordsMeta[match].score = sc;
            wordsSpans[match].className = 'word ' + colorByScore(sc);
            nextPtr = match+1;
          }}
        }}
        highlightWord(nextPtr);
        updateStats();
      }}

      function parseAny(e){{
        try {{
          const rawPA  = e?.result?.privPronunciationAssessmentJson || e?.privPronunciationAssessmentJson;
          const rawSTT = e?.result?.properties?.getProperty(SpeechSDK.PropertyId.SpeechServiceResponse_JsonResult);
          const raw = rawPA || rawSTT; if (!raw) return null;
          const j = JSON.parse(raw); if (DEBUG) dbg('json', j);
          return j;
        }} catch(_){{
          return null;
        }}
      }}

      startTime = Date.now();
      rec.recognizing = (s,e)=>{{ byId('status').textContent='🎙 Listening…'; const j=parseAny(e); if (j) applyFromJson(j); }};
      rec.recognized  = (s,e)=>{{ const j=parseAny(e); if (j) applyFromJson(j); }};
      rec.canceled = () => {{
        byId('status').textContent = '⚠️ Canceled';
      }};
      rec.sessionStarted = () => {{
        if (!startTime) startTime = Date.now();
        byId('status').textContent = '🎙 Session started';
      }};
      rec.sessionStopped = () => {{
        isReading = false;
        byId('status').textContent = '🛑 Session stopped';
        updateStats(true);
      }};
    }}

    // ----- Optional local recording (for replay) -----
    function startLocalRecord(){{
      chunks = [];
      navigator.mediaDevices.getUserMedia({{ audio:true }}).then(stream=>{{
        recording = new MediaRecorder(stream);
        recording.ondataavailable = e=>{{ if (e.data.size>0) chunks.push(e.data); }};
        recording.start();
      }}).catch(()=>{{}});
    }}
    function stopLocalRecord(){{
      return new Promise(resolve=>{{
        if (!recording) return resolve(null);
        recording.onstop = ()=>{{
          try {{ if (replayUrl) URL.revokeObjectURL(replayUrl); }} catch(_){{
          }}
          const blob = new Blob(chunks, {{ type:'audio/webm' }});
          replayUrl = URL.createObjectURL(blob);
          resolve(replayUrl);
        }};
        try {{ recording.stop(); }} catch(_){{
          resolve(null);
        }}
      }});
    }}

    // ----- Actions -----
    async function startReading(){{
      const p = passages[currentIndex] || {{}};
      const reference = String(p.polish||'');
      if (!reference.trim()) {{
        byId('status').textContent = '⚠️ No passage text found.';
        return;
      }}

      // Require internet for assessment (similar to flashcards/practice)
      if (!navigator.onLine) {{
        byId('status').textContent = '📴 Offline: reading assessment needs internet. You can still use "Listen (Polish)" if audio is cached.';
        return;
      }}

      if (!window.SpeechSDK) {{
        byId('status').textContent = '⚠️ Speech SDK not loaded. Check your connection and try again.';
        return;
      }}

      if (isReading) {{
        return; // already running
      }}
      isReading = true;

      // Reset per-word scoring
      wordsMeta.forEach((w,i)=>{{ w.score = null; wordsSpans[i].className = 'word'; }});
      highlightWord(0);
      startTime = Date.now();

      byId('btnStart').disabled = true;
      byId('btnStop').disabled = false;
      byId('btnReplay').disabled = true;
      byId('status').textContent = '🎙 Preparing microphone…';

      try {{
        await prewarmMic();
      }} catch(_){{
      }}

      // Pre-fetch token to avoid first-chunk latency
      try {{
        await fetchToken();
      }} catch(e) {{
        dbg('token error', e?.message || e);
        byId('status').textContent = '⚠️ Could not reach speech service. Please try again.';
        byId('btnStart').disabled = false;
        byId('btnStop').disabled = true;
        isReading = false;
        return;
      }}

      // Tiny warmup delay; helps Safari a bit
      await new Promise(r => setTimeout(r, 180));

      try {{
        recognizer = await makeRecognizer(reference);
      }} catch(e) {{
        dbg('makeRecognizer error', e?.message || e);
        byId('status').textContent = '⚠️ Could not start recognition.';
        byId('btnStart').disabled = false;
        byId('btnStop').disabled = true;
        isReading = false;
        return;
      }}

      attachHandlers(recognizer, reference);

      try {{
        await new Promise((resolve, reject) => {{
          try {{ recognizer.startContinuousRecognitionAsync(resolve, reject); }}
          catch(e) {{ reject(e); }}
        }});
        byId('status').textContent = '🎙 Listening…';
        startLocalRecord();
      }} catch(e) {{
        dbg('start error', e?.message || e);
        byId('status').textContent = '⚠️ Could not start recognition.';
        byId('btnStart').disabled = false;
        byId('btnStop').disabled = true;
        isReading = false;
      }}
    }}


    async function stopReading(){{
      if (!isReading && !recognizer) {{
        // Nothing to stop; just normalise buttons
        byId('btnStop').disabled = true;
        byId('btnStart').disabled = false;
        return;
      }}

      byId('btnStop').disabled = true;
      byId('status').textContent = '🛑 Stopping…';

      try {{
        if (recognizer) {{
          await new Promise(res => {{
            try {{
              recognizer.stopContinuousRecognitionAsync(() => res(), () => res());
            }} catch(_e) {{
              res();
            }}
          }});
        }}
      }} finally {{
        isReading = false;
        recognizer = null;
        const url = await stopLocalRecord();
        if (url) {{
          const a = byId('replayAudio'); a.src = url; a.load();
          byId('btnReplay').disabled = false;
        }}
        byId('btnStart').disabled = false;
        byId('status').textContent = '🛑 Stopped';
        updateStats(true);
      }}
    }}


    function listenPolish(){{
      const a = byId('ttsAudio');
      const p = passages[currentIndex] || {{}};
      const direct = p.audio_url || p.audio;
      let src = '';
      if (direct && /^https?:\\/\\//i.test(direct)) src = direct;
      else if (window.AudioPaths) src = AudioPaths.readingPath(setName, currentIndex, r2Manifest);
      else src = `../../static/${{encodeURIComponent(setName)}}/reading/${{encodeURIComponent(currentIndex)}}.mp3`;
      a.onerror = ()=> byId('status').textContent='🔇 Audio not found for this passage.';
      a.src = src;
      a.load();
      a.playbackRate = playbackRate;
      a.play().catch(()=> byId('status').textContent='🔇 Unable to play audio.');
    }}

    function replayMe(){{
      const a = byId('replayAudio'); if (!a.src) return;
      a.currentTime = 0; a.play().catch(()=>{{}});
    }}

    function toggleEN(){{
      const el = byId('translation');
      const vis = el.style.display !== 'none';
      el.style.display = vis ? 'none' : 'block';
      byId('btnToggleEN').textContent = vis ? '🇬🇧 Show Translation' : '🇬🇧 Hide Translation';
    }}
    function toggleSpeed(){{
      playbackRate = (playbackRate === 1.0) ? 0.8 : 1.0;
      const btn = byId('btnSpeed');
      if (!btn) return;
      if (playbackRate === 1.0) {{
        btn.textContent = '🏃 1.0×';
      }} else {{
        btn.textContent = '🐢 0.8×';
      }}
    }}

    // ----- Offline SW -----
    function readingAudioUrls(){{
      const urls = [];
      for (let i=0;i<passages.length;i++){{
        if (window.AudioPaths) urls.push(AudioPaths.readingPath(setName, i, r2Manifest));
        else urls.push(`../../static/${{encodeURIComponent(setName)}}/reading/${{encodeURIComponent(i)}}.mp3`);
      }}
      return Array.from(new Set(urls));
    }}
    async function ensureSW(){{
      if (!('serviceWorker' in navigator)) return null;
      try {{
        const reg = await navigator.serviceWorker.register('./sw.js', {{ scope:'./' }});
        await navigator.serviceWorker.ready;
        return reg;
      }} catch(e){{ dbg('sw fail', e?.message||e); return null; }}
    }}

    // ----- Wire UI -----
    function wire(){{
      byId('passageSelect').addEventListener('change', e=>{{ currentIndex = parseInt(e.target.value,10)||0; renderPassage(currentIndex); }});
      byId('btnStart').addEventListener('click', startReading);
      byId('btnStop').addEventListener('click', stopReading);
      byId('btnListen').addEventListener('click', listenPolish);
      byId('btnSpeed').addEventListener('click', toggleSpeed);
      byId('btnReplay').addEventListener('click', replayMe);
      byId('btnToggleEN').addEventListener('click', toggleEN);
      byId('btnFinish').addEventListener("click", finishSession);

      // Offline handlers
      const offlineBtn = byId('btnOffline');
      const offlineRmBtn = byId('btnOfflineRm');
      const offlineStatus = byId('offlineStatus');

      let swReg = null;

      if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1')) {{
        (async () => {{
          swReg = await ensureSW();
          if (!swReg) {{
            offlineBtn.style.display = 'none';
            offlineRmBtn.style.display = 'none';
            offlineStatus.textContent = 'Offline download is not available here, but you can still read while online.';
          }} else {{
            offlineStatus.textContent = 'Tap Offline to download audio for this set.';
          }}
        }})();
      }} else {{
        offlineBtn.style.display = 'none';
        offlineRmBtn.style.display = 'none';
        offlineStatus.textContent = 'Offline download is not available in this browser.';
      }}

      offlineBtn.addEventListener('click', async () => {{
        if (!swReg || !swReg.active) {{
          offlineStatus.textContent = '❌ Offline not available.';
          return;
        }}
        offlineStatus.textContent = '⬇️ Downloading…';
        swReg.active.postMessage({{ type:'CACHE_SET', cache:`reading-{set_name}`, urls: readingAudioUrls() }});
      }});

      offlineRmBtn.addEventListener('click', async () => {{
        if (!swReg || !swReg.active) return;
        swReg.active.postMessage({{ type:'UNCACHE_SET', cache:`reading-{set_name}` }});
      }});

      navigator.serviceWorker?.addEventListener('message', ev => {{
        const d = ev.data || {{}};
        if (!offlineStatus) return;
        if (d.type === 'CACHE_PROGRESS') offlineStatus.textContent = `⬇️ ${{d.done}} / ${{d.total}} files cached…`;
        else if (d.type === 'CACHE_DONE') {{
          offlineStatus.textContent = '✅ Available offline';
          offlineRmBtn.style.display = 'inline-flex';
        }} else if (d.type === 'UNCACHE_DONE') {{
          offlineStatus.textContent = '🗑 Removed offline copy';
          offlineRmBtn.style.display = 'none';
        }} else if (d.type === 'CACHE_ERROR') {{
          offlineStatus.textContent = '❌ Offline failed';
        }}
      }});


      // Page chrome auth state
      (async () => {{
        try {{
          const r = await api.fetch('/api/me');
          if (r.ok) {{
            byId('loginLink').style.display='none';
            byId('registerLink').style.display='none';
            byId('logoutBtn').style.display='inline-flex';
          }}
        }} catch(_){{
        }}
        byId('logoutBtn')?.addEventListener('click', async ()=>{{
          try {{ await api.fetch('/api/logout', {{method:'POST'}}); }} catch(_){{
          }}
          api.clearToken(); location.href='login.html';
        }});
      }})();
    }}

    // ----- Lifecycle -----
    (async function init(){{
      try {{ if (window.AudioPaths) r2Manifest = await AudioPaths.fetchManifest(setName); }} catch(_){{
        r2Manifest = null;
      }}
      populateSelect();
      renderPassage(0);

      // Preload first passage audio to reduce initial R2 hit
      try {{
        const a = byId('ttsAudio');
        const p0 = passages[0] || {{}};
        const direct = p0.audio_url || p0.audio;
        let src = '';
        if (direct && /^https?:\/\//i.test(direct)) src = direct;
        else if (window.AudioPaths) src = AudioPaths.readingPath(setName, 0, r2Manifest);
        else src = `../../static/${{encodeURIComponent(setName)}}/reading/0.mp3`;
        if (src) {{
          a.preload = 'auto';
          a.src = src;
          a.load();
        }}
        // Keep the active word roughly in sync with the Polish audio
        a.addEventListener('timeupdate', syncTtsProgress);
      }} catch(_){{
      }}

      wire();
      // Prefetch token to reduce latency
      fetchToken().catch(()=>{{}});

    }}();

    window.addEventListener('beforeunload', ()=>{{
      try {{ recognizer && recognizer.stopContinuousRecognitionAsync(); }} catch(_){{
      }}
      try {{ replayUrl && URL.revokeObjectURL(replayUrl); }} catch(_){{
      }}
    }});
    document.addEventListener('visibilitychange', ()=>{{
      if (document.hidden) try {{ recognizer && recognizer.stopContinuousRecognitionAsync(); }} catch(_){{
      }}
    }});

    function computeAvgScore(){{
      const done = wordsMeta.filter(w => typeof w.score === "number");
      if (!done.length) return 0;
      return done.reduce((a,b)=>a+b.score,0) / done.length;
    }}

    async function finishSession(){{
      const avg = Math.max(0, Math.min(100, Math.round(computeAvgScore())));
      const elapsed = Date.now() - startTime;

      const wordsDone = wordsMeta.filter(w => typeof w.score === "number");
      const wpm = computeWPM(elapsed, wordsDone.length);

      const p = passages[currentIndex] || {{}};
      const totalWords = wordsMeta.length;
      const recognizedWords = wordsDone.length;

      const rawLabel = p.title || (p.polish || '');
      let label = rawLabel ? String(rawLabel) : `Passage ${{currentIndex+1}}`;
      if (label.length > 60) label = label.slice(0, 57) + '…';

      const perKey = 'reading_' + currentIndex;
      const per = {{}};
      per[perKey] = {{
        best: avg,
        label,
        text: p.polish || ''
      }};

      const details = {{
        mode: 'reading',
        set: setName,
        passage_index: currentIndex,
        avg_accuracy: avg,
        wpm,
        total_words: totalWords,
        recognized_words: recognizedWords,
        total: 1,
        n100: avg >= 100 ? 1 : 0,
        avg_card_score: avg,
        per,
        words: wordsMeta
      }};

      try {{
        await Results.submit({{
          set: setName,
          mode: 'reading',
          score: avg,
          details
        }});
      }} finally {{
        Results.goSummary({{
          set: setName,
          mode: 'reading',
          score: avg,
          details
        }});
      }}
    }}


  </script>
</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8")

    # --- Service worker for offline reading audio ---
    sw_js = """/* reading SW */
self.addEventListener('install', (e) => { self.skipWaiting(); });
self.addEventListener('activate', (e) => { self.clients.claim(); });

function toAbs(u){
  try { return new URL(u, self.registration.scope || self.location.href).href; }
  catch(_) { return null; }
}

self.addEventListener('message', async (e) => {
  const data = e.data || {};
  const client = await self.clients.get(e.source && e.source.id);
  if (data.type === 'CACHE_SET') {
    const cacheName = data.cache || 'reading-cache';
    const urls = Array.isArray(data.urls) ? data.urls.map(toAbs).filter(Boolean) : [];
    try {
      const cache = await caches.open(cacheName);
      let done = 0, total = urls.length;
      for (const u of urls) {
        try {
          const res = await fetch(u, { mode: 'cors' });
          if (res.ok || res.type === 'opaque') {
            await cache.put(u, res.clone());
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
    const cacheName = data.cache || 'reading-cache';
    await caches.delete(cacheName);
    client && client.postMessage({ type: 'UNCACHE_DONE', cache: cacheName });
  }
});

// Cache-first if present; fall back to network
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
    (out_dir / "sw.js").write_text(sw_js, encoding="utf-8")

    print(f"✅ reading page generated: {out_path}")
    return out_path
