# app/practice.py
import json
from .sets_utils import sanitize_filename
from .constants import PAGES_DIR as DOCS_DIR

def generate_practice_html(set_name, data):
    """
    Generates:
      - docs/practice/<set_name>/index.html
      - docs/practice/<set_name>/sw.js (offline audio cache worker)

    Capture-first recognizer with VAD (fast & iOS/Safari-stable):
      - Plays native audio, then captures user speech (~1.4s max with early-stop)
      - Streams 16k/16-bit/mono PCM to Azure for Pronunciation Assessment
      - Strict scoring: 0.55*Accuracy + 0.25*Fluency + 0.20*Completeness,
        then penalize by voiced_ms coverage and Azure word error fraction.
      - Phoneme granularity + miscue enabled; word timestamps disabled.

    URL toggles:
      - ?debug=1   → debug overlay + WAV download link
      - ?live=1    → force live-mic path (recognizeOnce on default mic)
      - ?capture=0 → force live mode (default is capture)
    """
    # Ensure output dir exists
    output_dir = DOCS_DIR / "practice" / set_name
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "index.html"

    # Preserve your audio filename convention
    safe_data = []
    for idx, entry in enumerate(data):
        phrase = entry.get("phrase", "")
        entry = dict(entry)
        entry["audio_file"] = f"{idx}_{sanitize_filename(phrase)}.mp3"
        safe_data.append(entry)

    cards_json = json.dumps(safe_data, ensure_ascii=False).replace(r"</", r"<\/")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />

  <!-- Dual-host <base>: GitHub Pages vs Flask -->
  <script>
    (function () {{
      var isGH = /\\.github\\.io$/i.test(location.hostname);
      var baseHref = isGH ? '/LearnPolish/' : '/';
      document.write('<base href="' + baseHref + '">');
    }})();
  </script>

  <title>{set_name} • Speak • Path to POLISH</title>
  <link rel="stylesheet" href="static/app.css?v=5" />

  <style>
    .wrap{{ max-width:900px; margin:0 auto; padding:0 16px 88px; }}
    .stack{{ display:grid; gap:16px }}
    .row{{ display:flex; gap:10px; align-items:center; flex-wrap:wrap }}
    .card{{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:16px }}

    .head{{ display:flex; align-items:center; justify-content:space-between }}
    .title{{ font-size:18px; font-weight:700 }}

    .prompt{{ font-size:18px; color:var(--muted) }}
    .phrase{{ font-size:22px; font-weight:800; margin-top:6px }}
    .result{{ margin-top:8px; min-height:1.2em }}

    .btn{{ display:inline-flex; align-items:center; gap:8px; padding:10px 14px; border-radius:10px;
          border:1px solid var(--border); background:var(--card); cursor:pointer }}
    .btn-primary{{ background:var(--brand); border-color:var(--brand); color:#fff }}
    .btn:disabled{{ opacity:.6; cursor:default }}

    /* Level meter (capture mode) */
    #meterWrap{{ display:none; margin-top:10px; width:260px; height:8px; background:#e6e6ef; border-radius:999px; overflow:hidden }}
    #meterBar{{ width:0%; height:100%; background:var(--brand) }}

    /* Debug overlay */
    #dbg{{ display:none; position:fixed; bottom:8px; left:8px; right:8px; max-height:46vh; overflow:auto;
          background:#000; color:#0f0; padding:8px 10px; border-radius:10px; font-family:ui-monospace, SFMono-Regular, Menlo, monospace;
          font-size:12px; white-space:pre-wrap; z-index:9999 }}
    #dbg .raw{{ color:#9ef }}
  </style>
</head>
<body
  data-header="Path to Polish"
  data-note-lead="Speak"
  data-note-tail="{set_name}"
  style="--logo-size: 40px; --banner-size: 24px; --banner-size-lg: 30px">

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
      <div class="head">
        <div class="title">Practice: repeat after me</div>
        <div class="row">
          <button id="startBtn" class="btn btn-primary">▶️ Start</button>
          <button id="pauseBtn" class="btn" style="display:none;">⏸ Pause</button>
          <button id="restartBtn" class="btn" style="display:none;">🔁 Restart</button>
          <a id="dlWav" class="btn" download="capture.wav" style="display:none;">⬇️ Capture</a>
        </div>
      
      </div>
      <div class="row" style="margin-top:8px; gap:6px; flex-wrap:wrap;">
        <span class="muted" style="font-size:13px;">Difficulty:</span>
        <button type="button" class="btn tiny diff-btn" data-diff="easy">Easy</button>
        <button type="button" class="btn tiny diff-btn" data-diff="normal">Normal</button>
        <button type="button" class="btn tiny diff-btn" data-diff="hard">Hard</button>
      </div>

      <div id="prompt" class="prompt">Get ready…</div>
      <div id="phrase" class="phrase">—</div>
      <div id="meaning" class="prompt" style="margin-top:4px; font-size:16px;"></div>
      <div id="meterWrap"><div id="meterBar"></div></div>
      <div id="result" class="result"></div>

    </section>

    <section class="card">
      <div class="title">Offline audio</div>
      <div class="row" style="margin-top:8px">
        <button id="offlineBtn" class="btn">⬇️ Download</button>
        <button id="offlineRemoveBtn" class="btn" style="display:none;">🗑 Remove</button>
        <span id="offlineStatus" class="result" style="margin:0"></span>
      </div>
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

  <!-- Scripts (base href makes these root-relative) -->
  <script src="static/js/app-config.js"></script>
  <script src="static/js/api.js"></script>
  <script src="static/js/page-chrome.js" defer></script>
  <script src="static/js/audio-paths.js"></script>
  <script src="static/js/results.js"></script>
  <script src="https://aka.ms/csspeech/jsbrowserpackageraw"></script>

  <script>
    // ===== State =====
    const setName = "{set_name}";
    const cards = {cards_json};

    const DIFF_PRESETS = {{ easy: 65, normal: 75, hard: 85 }};
    let difficulty = (localStorage.getItem("lp.diff_practice") || "normal");
    function currentPassThreshold() {{
      return DIFF_PRESETS[difficulty] || 75;
    }}

    function applyDifficultyUI() {{
      const btns = document.querySelectorAll(".diff-btn");
      btns.forEach(btn => {{
        const d = btn.dataset.diff;
        if (d === difficulty) btn.classList.add("btn-primary");
        else btn.classList.remove("btn-primary");
      }});
    }}

    function wireDifficulty() {{
      const btns = document.querySelectorAll(".diff-btn");
      if (!btns.length) return;
      btns.forEach(btn => {{
        btn.addEventListener("click", (e) => {{
          e.preventDefault();
          const d = btn.dataset.diff || "normal";
          difficulty = d;
          try {{ localStorage.setItem("lp.diff_practice", difficulty); }} catch (_) {{}}
          applyDifficultyUI();
        }});
      }});
      applyDifficultyUI();
    }}


    let hasStarted = false, paused = false, isRunning = false;
    let index = 0, attempts = 0;

    // Track per-card best scores for this run
    const tracker = {{
      per: {{}},     // key: card index -> best/last/attempts/phrase
      attempts: 0    // total scoring attempts this run
    }};

    // Debug overlay
    const DEBUG = new URL(location.href).searchParams.get('debug') === '1';
    const dbgEl = document.getElementById('dbg');
    if (DEBUG) dbgEl.style.display = 'block';
    function logDbg(...a){{
      if (!DEBUG) return;
      const line = document.createElement('div');
      line.textContent = a.map(x => (typeof x === 'string'? x : JSON.stringify(x))).join(' ');
      dbgEl.appendChild(line); dbgEl.scrollTop = dbgEl.scrollHeight;
      try{{ console.debug('[Practice]', ...a); }}catch(_){{
      }}
    }}
    function logRaw(j){{
      if (!DEBUG) return;
      const line = document.createElement('div');
      line.className = 'raw';
      line.textContent = (typeof j === 'string') ? j : JSON.stringify(j);
      dbgEl.appendChild(line); dbgEl.scrollTop = dbgEl.scrollHeight;
    }}

    // URL overrides (default capture)
    const URLP = new URL(location.href).searchParams;
    const FORCE_LIVE = URLP.get('live') === '1';
    const capQ = URLP.get('capture');
    const CAPTURE_MODE = FORCE_LIVE ? false : (capQ === '0' ? false : true);

    // Manifest/CDN optional
    let r2Manifest = null;

    // UI els
    const promptEl = document.getElementById('prompt');
    const phraseEl = document.getElementById('phrase');
    const meaningEl = document.getElementById('meaning');
    const resultEl = document.getElementById('result');
    const meterWrap = document.getElementById('meterWrap');
    const meterBar  = document.getElementById('meterBar');
    const dlWav     = document.getElementById('dlWav');

    // Audio preload
    const audioCache = new Map();
    function sanitizeFilename(text){{
      return (text || "")
        .normalize("NFD").replace(/[\\u0300-\\u036f]/g, "")
        .replace(/[^a-zA-Z0-9_-]+/g, "_").replace(/^_+|_+$/g, "");
    }}
    function buildAudioSrc(i){{
      const e = cards[i] || {{}};
      const local = "static/" + encodeURIComponent(setName) + "/audio/" + encodeURIComponent(e.audio_file || (i + "_.mp3"));
      try {{
        if (window.AudioPaths) return AudioPaths.buildAudioPath(setName, i, e, r2Manifest);
      }} catch(_){{
      }}
      return local;
    }}
    function primeAudio(i){{
      if (i < 0 || i >= cards.length || audioCache.has(i)) return;
      const a = new Audio(); a.preload = "auto"; a.src = buildAudioSrc(i);
      try{{ a.load(); }}catch(_){{
      }} audioCache.set(i, a);
    }}
    function playAudio(i){{
      return new Promise(resolve => {{
        let a = audioCache.get(i);
        if (!a) {{ primeAudio(i); a = audioCache.get(i); }}
        if (!a) return resolve();
        a.currentTime = 0;
        a.onended = resolve;
        a.onerror = resolve;
        const p = a.play(); if (p) p.catch(_=>resolve());
      }});
    }}

    // System prompts
    function sysUrl(name){{ return "static/system_audio/" + name + ".mp3"; }}
    function playSys(name){{
      return new Promise(resolve => {{
        const a = new Audio(sysUrl(name));
        a.onended = resolve; a.onerror = resolve;
        const p = a.play(); if (p) p.catch(_=>resolve());
      }});
    }}

    // Token cache
    const tokenCache = {{ token:null, region:null, exp:0 }};
    async function fetchToken(){{
      const now = Date.now();
      if (tokenCache.token && tokenCache.region && now < tokenCache.exp) return tokenCache;
      try {{
        const tok = await api.get('/api/speech_token', {{ noAuth: true }});
        const token  = tok && (tok.token || tok.access_token);
        const region = tok && (tok.region || tok.location || tok.regionName);
        if (!token || !region) throw new Error('no_token_or_region');
        tokenCache.token = token; tokenCache.region = region; tokenCache.exp = now + 9*60*1000;
        logDbg('SDK?', !!window.SpeechSDK, 'region', region, 'tok', !!token);
        return tokenCache;
      }} catch(e){{
        logDbg('token error', e?.message || e); return {{ token:null, region:null, exp:0 }};
      }}
    }}
    async function prefetchToken(){{
      try {{ await fetchToken(); }} catch(_){{
      }}
    }}

    // VAD capture (~1.4s max, early-stop on silence)
    async function recordBlobVAD(maxMs=2200){{
      meterWrap.style.display = CAPTURE_MODE ? 'block' : 'none';
      let mediaStream=null, mediaRec=null, chunks=[];
      let analyser=null, data=null, ctx=null, src=null;
      let meterTimer=null, started=false, silentMs=0, voicedMs=0, startedAt=0;

      try {{
        mediaStream = await navigator.mediaDevices.getUserMedia({{ audio:true }});
        try {{
          const ACtx = window.AudioContext || window.webkitAudioContext;
          if (ACtx) {{
            ctx = new ACtx(); src = ctx.createMediaStreamSource(mediaStream);
            analyser = ctx.createAnalyser(); analyser.fftSize = 2048; src.connect(analyser);
            data = new Uint8Array(analyser.fftSize);
          }}
        }} catch(_){{
        }}

        mediaRec = new MediaRecorder(mediaStream, {{ mimeType: 'audio/webm' }});
        mediaRec.ondataavailable = e => {{ if (e.data && e.data.size) chunks.push(e.data); }};
        const stopNow = () => {{ try {{ if (mediaRec && mediaRec.state !== 'inactive') mediaRec.stop(); }} catch(_){{
        }} }};
        mediaRec.start();

        const t0 = performance.now();
        const THRESH = 0.038, SIL_HOLD = 420; // match flashcards

        await new Promise((resolve) => {{
          meterTimer = setInterval(() => {{
            const t = performance.now();
            if (analyser && data){{
              analyser.getByteTimeDomainData(data);
              let sum=0; for(let i=0;i<data.length;i++){{ const v=(data[i]-128)/128; sum+=v*v; }}
              const rms = Math.sqrt(sum/data.length);
              meterBar.style.width = Math.min(100, Math.round(rms*180)) + '%';

              if (!started && rms > THRESH) {{ started = true; startedAt = t; }}
              else if (started) {{
                if (rms > THRESH*0.75) voicedMs += 40;
                if (rms < THRESH*0.6) silentMs += 40; else silentMs = 0;
                if (silentMs >= SIL_HOLD && (t - startedAt) > 260) stopNow();
              }}
            }}
            if ((t - t0) > maxMs) stopNow();
          }}, 40);
          mediaRec.onstop = resolve;
        }});

        return {{ blob: new Blob(chunks, {{ type:'audio/webm' }}), voicedMs }};
      }} finally {{
        try {{ if (meterTimer) clearInterval(meterTimer); }} catch(_){{
        }}
        try {{ meterBar.style.width='0%'; }} catch(_){{
        }}
        try {{ mediaStream && mediaStream.getTracks().forEach(t=>t.stop()); }} catch(_){{
        }}
        try {{ ctx && ctx.close(); }} catch(_){{
        }}
        meterWrap.style.display = 'none';
      }}
    }}

    async function blobToPCM16Mono(blob, targetRate=16000){{
      const arr = await blob.arrayBuffer();
      const ACtx = window.AudioContext || window.webkitAudioContext;
      if (!ACtx) throw new Error('no_audiocontext');
      const ctx = new ACtx();
      const buf = await ctx.decodeAudioData(arr.slice(0));
      const chL = buf.getChannelData(0);
      let mono;
      if (buf.numberOfChannels > 1){{
        const chR = buf.getChannelData(1);
        mono = new Float32Array(buf.length);
        for(let i=0;i<buf.length;i++) mono[i] = 0.5*(chL[i] + chR[i]);
      }} else mono = chL;
      const ratio = buf.sampleRate / targetRate;
      const outLen = Math.round(mono.length / ratio);
      const out = new Float32Array(outLen);
      for (let i=0;i<outLen;i++) {{
        const idx = i*ratio, i0 = Math.floor(idx), i1 = Math.min(i0+1, mono.length-1), frac = idx - i0;
        out[i] = mono[i0]*(1-frac) + mono[i1]*frac;
      }}
      const pcm = new Int16Array(outLen);
      for (let i=0;i<outLen;i++) {{
        let v = Math.max(-1, Math.min(1, out[i])); pcm[i] = v < 0 ? v * 0x8000 : v * 0x7FFF;
      }}
      try {{ ctx.close(); }} catch(_){{
      }}
      return pcm;
    }}
    function pcmToWavBlob(pcm, sampleRate=16000){{
      const numFrames = pcm.length, bps=2, block=bps, byteRate=sampleRate*block, dataSize=numFrames*bps;
      const buf = new ArrayBuffer(44 + dataSize), v = new DataView(buf); let o=0;
      function wstr(s){{ for(let i=0;i<s.length;i++) v.setUint8(o++, s.charCodeAt(i)); }}
      function wu16(x){{ v.setUint16(o, x, true); o+=2; }} function wu32(x){{ v.setUint32(o, x, true); o+=4; }}
      wstr('RIFF'); wu32(36 + dataSize); wstr('WAVE'); wstr('fmt '); wu32(16); wu16(1); wu16(1);
      wu32(sampleRate); wu32(byteRate); wu16(block); wu16(16); wstr('data'); wu32(dataSize);
      for(let i=0;i<pcm.length;i++) v.setInt16(o + i*2, pcm[i], true);
      return new Blob([v], {{ type:'audio/wav' }});
    }}

    // Strict scoring helpers
    function estimateSyllablesPL(text){{
      const t = String(text||'').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');
      const m = t.match(/[aąeęiouyó]/g);
      return Math.max(1, m ? m.length : 0);
    }}
    function computeCaptureWindowMs(text){{
      const syll = estimateSyllablesPL(text);
      const base = 900;
      const per  = 220;
      const min  = 1400;
      const max  = 3200;
      return Math.max(min, Math.min(max, base + per * syll));
    }}
    function extractPAJson(result, SDK){{
      try {{
        const raw = result?.properties?.getProperty(SDK.PropertyId.SpeechServiceResponse_JsonResult)
                 || result?.privPronunciationAssessmentJson || result?.privJson;
        if (!raw) return null;
        try {{ return JSON.parse(raw); }} catch(_){{
          return null;
        }}
      }} catch(_){{
        return null;
      }}
    }}
    function extractBaseMetrics(result, SDK){{
      try {{
        const pa = SDK.PronunciationAssessmentResult.fromResult(result);
        if (pa) return {{ acc: Math.round(pa.accuracyScore||0), flu: Math.round(pa.fluencyScore||0), comp: Math.round(pa.completenessScore||0) }};
      }} catch(_){{
      }}
      return {{ acc:0, flu:0, comp:0 }};
    }}
        function computeStrictScore(paJson, base, refText, voicedMs){{
      let acc = base.acc || 0, flu = base.flu || 0, comp = base.comp || 0, wordErrFrac = 0;
      if (paJson){{
        const top = (paJson.NBest && paJson.NBest[0]) ? paJson.NBest[0] : null;
        const pa  = top?.PronunciationAssessment || paJson.PronunciationAssessment;
        if (pa){{
          acc = Math.round(Number(pa.AccuracyScore) || acc);
          flu = Math.round(Number(pa.FluencyScore)  || flu);
          comp= Math.round(Number(pa.CompletenessScore) || comp);
        }}
        const words = top?.Words || paJson.Words || [];
        const refCount = Math.max(1, String(refText||'').trim().split(/\s+/).length);
        let errs=0; for(const w of words){{ const et=w?.PronunciationAssessment?.ErrorType; if (et && et !== 'None') errs++; }}
        wordErrFrac = Math.max(0, Math.min(1, errs/refCount));
      }}
      let baseScore = Math.round(0.55*acc + 0.25*flu + 0.20*comp);
      const syll = estimateSyllablesPL(refText);
      const targetMs = Math.max(320, Math.min(1600, 280 + 110*syll));
      const needed   = 0.85 * targetMs;
      const energyF  = Math.max(0.4, Math.min(1, (voicedMs||0)/needed));
      const errF     = 1 - 0.65*wordErrFrac;
      let strict = Math.round(baseScore * energyF * errF);
      strict = Math.max(0, Math.min(100, strict));
      return {{ strict, acc, flu, comp, wordErrFrac, energyF }};
    }}

    async function assessCapture(referenceText){{
      const ref = (referenceText||"").trim();
      const empty = {{ score: 0, acc: 0, flu: 0, comp: 0 }};
      if (!window.SpeechSDK) return empty;
      if (!ref) return empty;

      if (!navigator.onLine) {{
        resultEl.textContent = "📴 Offline: scoring needs internet, but you can still listen and repeat.";
        return empty;
      }}

      resultEl.textContent = "🎤 Recording…";
      const dynMax = computeCaptureWindowMs(ref);
      const rec = await recordBlobVAD(dynMax);
      const {{ token, region }} = await fetchToken();
      if (!token || !region) {{
        resultEl.textContent = "⚠️ Token/region issue";
        return empty;
      }}

      const pcm = await blobToPCM16Mono(rec.blob, 16000);
      if (DEBUG) try {{
        const url = URL.createObjectURL(pcmToWavBlob(pcm, 16000));
        dlWav.href = url; dlWav.style.display='inline-flex';
      }} catch(_){{
      }}

      const SDK = window.SpeechSDK;
      const speechConfig = SDK.SpeechConfig.fromAuthorizationToken(token, region);
      speechConfig.speechRecognitionLanguage = "pl-PL";
      speechConfig.outputFormat = SDK.OutputFormat.Detailed;
      speechConfig.setProperty(SDK.PropertyId.SpeechServiceResponse_RequestDetailedResultTrueFalse, "true");
      speechConfig.setProperty(SDK.PropertyId.SpeechServiceResponse_RequestWordLevelTimestamps, "false");

      const format = SDK.AudioStreamFormat.getWaveFormatPCM(16000, 16, 1);
      const push = SDK.AudioInputStream.createPushStream(format);
      push.write(new Uint8Array(pcm.buffer)); push.close();
      const audioConfig = SDK.AudioConfig.fromStreamInput(push);

      const recognizer = new SDK.SpeechRecognizer(speechConfig, audioConfig);
      const pa = new SDK.PronunciationAssessmentConfig(
        ref,
        SDK.PronunciationAssessmentGradingSystem.HundredMark,
        SDK.PronunciationAssessmentGranularity.Phoneme,
        true
      );
      pa.applyTo(recognizer);
      try {{ SDK.PhraseListGrammar.fromRecognizer(recognizer)?.add(ref); }} catch(_){{
      }}

      resultEl.textContent = "🧠 Scoring…";
      const result = await new Promise((resolve, reject) => {{
        try {{ recognizer.recognizeOnceAsync(resolve, reject); }} catch(e) {{ reject(e); }}
      }}).catch(e => {{ logDbg('recognizeOnce(push) error', e?.message || e); return null; }});
      try {{ recognizer.close(); }} catch(_){{
      }}
      if (!result) {{
        resultEl.textContent = "⚠️ Speech error";
        return empty;
      }}

      try {{
        const SDKR = window.SpeechSDK;
        if (result?.reason === SDKR.ResultReason.Canceled) {{
          const c = SDKR.CancellationDetails.fromResult(result);
          logDbg('canceled', c?.reason, c?.errorCode);
        }}
        const raw = result?.properties?.getProperty(SDK.PropertyId.SpeechServiceResponse_JsonResult)
                 || result?.privPronunciationAssessmentJson || result?.privJson;
        if (raw) try {{ logRaw(JSON.parse(raw)); }} catch(_){{
          logRaw(raw);
        }}
      }} catch(_){{
      }}

      const base = extractBaseMetrics(result, SDK);
      const paJson = extractPAJson(result, SDK);
      const {{ strict, acc, flu, comp }} = computeStrictScore(paJson, base, ref, rec.voicedMs);

      if (strict) {{
        resultEl.textContent = `✅ ${{strict}}%  (Acc ${{acc}} · Flu ${{flu}} · Comp ${{comp}})`;
      }} else {{
        resultEl.textContent = "⚠️ No score";
      }}
      return {{ score: strict || 0, acc, flu, comp }};
    }}

    async function assessLive(referenceText){{
      const ref = (referenceText||"").trim();
      const empty = {{ score: 0, acc: 0, flu: 0, comp: 0 }};
      if (!window.SpeechSDK) return empty;
      if (!ref) return empty;

      if (!navigator.onLine) {{
        resultEl.textContent = "📴 Offline: scoring needs internet.";
        return empty;
      }}

      // brief warm-up
      try {{
        const s = await navigator.mediaDevices.getUserMedia({{ audio:true }});
        s.getTracks().forEach(t=>t.stop());
      }} catch(_){{
      }}

      const {{ token, region }} = await fetchToken();
      if (!token || !region) {{
        resultEl.textContent = "⚠️ Token/region issue";
        return empty;
      }}

      const SDK = window.SpeechSDK;
      const speechConfig = SDK.SpeechConfig.fromAuthorizationToken(token, region);
      speechConfig.speechRecognitionLanguage = "pl-PL";
      speechConfig.outputFormat = SDK.OutputFormat.Detailed;
      speechConfig.setProperty(SDK.PropertyId.SpeechServiceResponse_RequestDetailedResultTrueFalse, "true");
      speechConfig.setProperty(SDK.PropertyId.SpeechServiceResponse_RequestWordLevelTimestamps, "false");
      // More forgiving timeouts so users can think + finish
      speechConfig.setProperty(SDK.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "2600");
      speechConfig.setProperty(SDK.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "800");

      const audioConfig = SDK.AudioConfig.fromDefaultMicrophoneInput();
      const recognizer = new SDK.SpeechRecognizer(speechConfig, audioConfig);
      const pa = new SDK.PronunciationAssessmentConfig(
        ref,
        SDK.PronunciationAssessmentGradingSystem.HundredMark,
        SDK.PronunciationAssessmentGranularity.Phoneme,
        true
      );
      pa.applyTo(recognizer);
      try {{ SDK.PhraseListGrammar.fromRecognizer(recognizer)?.add(ref); }} catch(_){{
      }}

      resultEl.textContent = "🎙 Listening…";
      const result = await new Promise((resolve, reject) => {{
        try {{ recognizer.recognizeOnceAsync(resolve, reject); }} catch(e) {{ reject(e); }}
      }}).catch(e => {{ logDbg('recognizeOnce(live) error', e?.message || e); return null; }});
      try {{ recognizer.close(); }} catch(_){{
      }}
      if (!result) {{
        resultEl.textContent = "⚠️ Speech error";
        return empty;
      }}

      const base = extractBaseMetrics(result, SDK);
      const paJson = extractPAJson(result, SDK);
      // Approx voiced time for live path
      const syll = estimateSyllablesPL(ref);
      const approxVoiced = Math.max(320, Math.min(1600, 280 + 110*syll)) * 0.7;
      const {{ strict, acc, flu, comp }} = computeStrictScore(paJson, base, ref, approxVoiced);

      if (strict) {{
        resultEl.textContent = `✅ ${{strict}}%  (Acc ${{acc}} · Flu ${{flu}} · Comp ${{comp}})`;
      }} else {{
        resultEl.textContent = "⚠️ No score";
      }}
      return {{ score: strict || 0, acc, flu, comp }};
    }}

    // Finish: compute score, send to API, go to summary
    async function finishPractice() {{
      const totalCards = Math.max(1, cards.length);
      const perStats = Object.values(tracker.per || {{}});

      let sumBest = 0;
      let n100 = 0;
      let nPass = 0;
      const passNow = currentPassThreshold();

      // For transparency: average Acc / Flu / Comp across cards
      let sumAcc = 0;
      let sumFlu = 0;
      let sumComp = 0;
      let countMetrics = 0;

      for (const r of perStats) {{
        const best = Number((r && r.best) || 0);
        if (Number.isFinite(best)) {{
          const clamped = Math.max(0, Math.min(100, best));
          sumBest += clamped;
          if (clamped >= 100) n100++;
          if (clamped >= passNow) nPass++;
        }}

        const bestAcc  = Number((r && r.bestAcc)  || 0);
        const bestFlu  = Number((r && r.bestFlu)  || 0);
        const bestComp = Number((r && r.bestComp) || 0);
        if (Number.isFinite(bestAcc) || Number.isFinite(bestFlu) || Number.isFinite(bestComp)) {{
          sumAcc  += Math.max(0, Math.min(100, (bestAcc  || 0)));
          sumFlu  += Math.max(0, Math.min(100, (bestFlu  || 0)));
          sumComp += Math.max(0, Math.min(100, (bestComp || 0)));
          countMetrics++;
        }}
      }}

      // Average best-score across all cards (unseen cards count as 0)
      const avgScore = totalCards ? Math.round(sumBest / totalCards) : 0;
      const scorePct = avgScore;

      const denom = totalCards || countMetrics || 1;
      const avgAcc = Math.round(sumAcc / denom);
      const avgFlu = Math.round(sumFlu / denom);
      const avgComp = Math.round(sumComp / denom);

      // Build compact per-card breakdown with phrase text & per-metrics
      const perOut = {{}};
      Object.entries(tracker.per || {{}}).forEach(([idxStr, r]) => {{
        const idx = Number(idxStr);
        const card = cards[idx] || {{}};
        perOut[idx] = {{
          best: Number((r && r.best) || 0),
          last: Number((r && r.last) || 0),
          attempts: Number((r && r.attempts) || 0),
          bestAcc: Number((r && r.bestAcc) || 0),
          bestFlu: Number((r && r.bestFlu) || 0),
          bestComp: Number((r && r.bestComp) || 0),
          lastAcc: Number((r && r.lastAcc) || 0),
          lastFlu: Number((r && r.lastFlu) || 0),
          lastComp: Number((r && r.lastComp) || 0),
          phrase: card.phrase || ""
        }};
      }});

      // Cache global lastResult so /summary.html can show it
      try {{
        sessionStorage.setItem(
          "lp.lastResult",
          JSON.stringify({{
            set: setName,
            mode: "practice",
            score: scorePct,
            attempts: tracker.attempts,
            details: {{
              total: totalCards,
              n100,
              n_pass: nPass,
              metrics: {{
                acc: avgAcc,
                flu: avgFlu,
                comp: avgComp
              }},
              per: perOut
            }},
            ts: Date.now()
          }})
        );
      }} catch (_e) {{}}

      // Submit to backend (other-modes path in /api/submit_score handles gold & caps)
      let awarded = null;
      try {{
        const resp = await api.fetch("/api/submit_score", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            set_name: setName,
            mode: "practice",
            score: scorePct,
            attempts: tracker.attempts,
            details: {{
              total: totalCards,
              n100,
              n_pass: nPass,
              metrics: {{
                acc: avgAcc,
                flu: avgFlu,
                comp: avgComp
              }},
              per: perOut,
              difficulty,
              pass_threshold: currentPassThreshold()
            }}
          }})
        }});
        if (resp.ok) {{
          const js = await resp.json();
          if (js && js.details && js.details.points_awarded != null) {{
            awarded = Number(js.details.points_awarded);
          }}
        }}
      }} catch (_e) {{}}

      const q = awarded != null ? ("?awarded=" + encodeURIComponent(awarded)) : "";
      window.location.href = "summary.html" + q;
    }}


    // Loop
    async function runPractice() {{
      if (paused || isRunning) return;

      // End of set → compute score, send to API, go to summary
      if (index >= cards.length) {{
        promptEl.textContent = "Done!";
        phraseEl.textContent = "";
        resultEl.textContent = "✅ Complete";
        await finishPractice();
        return;
      }}

      isRunning = true;

      // Update UI
      const card = cards[index] || {{}};
      const phrase = card.phrase || "";
      const meaning = card.meaning || "";

      promptEl.textContent = "Listen:";
      phraseEl.textContent = phrase;
      meaningEl.textContent = meaning;
      resultEl.textContent = "";

      // Play Polish
      await playAudio(index);
      if (paused) {{ isRunning = false; return; }}

      // User says it
      promptEl.textContent = "Say:";
      const res = CAPTURE_MODE ? await assessCapture(phrase) : await assessLive(phrase);
      if (paused) {{ isRunning = false; return; }}

      const score = res && Number.isFinite(res.score) ? res.score : 0;
      const acc   = res && Number.isFinite(res.acc)   ? res.acc   : 0;
      const flu   = res && Number.isFinite(res.flu)   ? res.flu   : 0;
      const comp  = res && Number.isFinite(res.comp)  ? res.comp  : 0;

      // Update per-card tracker
      tracker.attempts++;
      const k = index;
      const prev = tracker.per[k] || {{
        best: 0, last: 0, attempts: 0,
        bestAcc: 0, bestFlu: 0, bestComp: 0,
        lastAcc: 0, lastFlu: 0, lastComp: 0
      }};
      prev.attempts = (prev.attempts || 0) + 1;
      prev.last = score;
      prev.lastAcc = acc;
      prev.lastFlu = flu;
      prev.lastComp = comp;
      if (!Number.isFinite(prev.best) || score > prev.best) {{
        prev.best = score;
      }}
      if (Number.isFinite(acc) && acc > (prev.bestAcc || 0)) prev.bestAcc = acc;
      if (Number.isFinite(flu) && flu > (prev.bestFlu || 0)) prev.bestFlu = flu;
      if (Number.isFinite(comp) && comp > (prev.bestComp || 0)) prev.bestComp = comp;
      tracker.per[k] = prev;

      // Feedback sound based on difficulty threshold
      const passNow = currentPassThreshold();
      try {{
        if (score >= passNow) await playSys("good");
        else await playSys("try_again");
      }} catch (_){{
      }}

      index++;
      attempts = 0;

      isRunning = false;
      if (!paused) setTimeout(runPractice, 600);
    }}

    // Offline SW
    async function ensureSW(){{
      if (!('serviceWorker' in navigator)) return null;
      try {{
        const reg = await navigator.serviceWorker.register('./sw.js', {{ scope: './' }});
        await navigator.serviceWorker.ready;
        return reg;
      }} catch(e){{ logDbg('SW register failed', e?.message || e); return null; }}
    }}
    function allAudioUrls(){{
      const urls = [];
      for (let i=0;i<cards.length;i++) urls.push(buildAudioSrc(i));
      ['repeat_after_me','good','try_again'].forEach(n => urls.push(sysUrl(n)));
      return Array.from(new Set(urls));
    }}

    // Startup
    document.addEventListener('DOMContentLoaded', async () => {{
      // Prefetch token & manifest; preload first clips
      prefetchToken().catch(()=>{{}});
      try {{ r2Manifest = await AudioPaths.fetchManifest(setName); }} catch(_){{
        r2Manifest = null;
      }}
      primeAudio(0); primeAudio(1);

      // Offline buttons
      const offlineBtn = document.getElementById('offlineBtn');
      const offlineRemoveBtn = document.getElementById('offlineRemoveBtn');
      const offlineStatus = document.getElementById('offlineStatus');

      // Try to register SW only where it's allowed (https or localhost)
      let swReg = null;
      if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1')) {{
        swReg = await ensureSW();
      }}

      if (!swReg) {{
        // Hide action buttons; leave a calm note instead of a scary error
        offlineBtn.style.display = "none";
        offlineRemoveBtn.style.display = "none";
        offlineStatus.textContent = "Offline download isn't available here, but you can still practice while online.";
      }} else {{
        offlineStatus.textContent = "Tap Download to make this set available offline.";
      }}

      navigator.serviceWorker?.addEventListener('message', (ev) => {{
        const d = ev.data || {{}};
        if (d.type === 'CACHE_PROGRESS') {{
          offlineStatus.textContent = `⬇️ ${{d.done}} / ${{d.total}} files cached…`;
        }} else if (d.type === 'CACHE_DONE') {{
          offlineStatus.textContent = "✅ Available offline";
          offlineRemoveBtn.style.display = "inline-flex";
        }} else if (d.type === 'UNCACHE_DONE') {{
          offlineStatus.textContent = "🗑 Removed offline copy";
          offlineRemoveBtn.style.display = "none";
        }} else if (d.type === 'CACHE_ERROR') {{
          offlineStatus.textContent = "❌ Offline failed";
        }}
      }});

      offlineBtn.addEventListener('click', async () => {{
        if (!swReg || !swReg.active) {{
          offlineStatus.textContent = "❌ Offline not available.";
          return;
        }}
        offlineStatus.textContent = "⬇️ Downloading…";
        swReg.active.postMessage({{ type:'CACHE_SET', cache:`practice-{set_name}`, urls: allAudioUrls() }});
      }});

      offlineRemoveBtn.addEventListener('click', async () => {{
        if (!swReg || !swReg.active) return;
        swReg.active.postMessage({{ type:'UNCACHE_SET', cache:`practice-{set_name}` }});
      }});


      // Controls
      const startBtn = document.getElementById('startBtn');
      const pauseBtn = document.getElementById('pauseBtn');
      const restartBtn = document.getElementById('restartBtn');

      startBtn.addEventListener('click', async () => {{
        if (hasStarted) return;
        hasStarted = true; paused = false;
        startBtn.style.display='none'; pauseBtn.style.display='inline-flex'; restartBtn.style.display='inline-flex';
        // User gesture established: play prompt + run
        await playSys('repeat_after_me');
        runPractice();
      }});

      pauseBtn.addEventListener('click', async () => {{
        if (!hasStarted) return;
        paused = !paused;
        pauseBtn.textContent = paused ? '▶️ Resume' : '⏸ Pause';
        if (!paused && !isRunning) {{
          await playSys('repeat_after_me');
          runPractice();
        }}
      }});

      restartBtn.addEventListener('click', async () => {{
        paused = false; index = 0; attempts = 0; isRunning = false;
        pauseBtn.textContent = '⏸ Pause';
        await playSys('repeat_after_me');
        runPractice();
      }});

      // Page chrome auth state
      try {{
        const r = await api.fetch('/api/me');
        if (r.ok) {{
          document.getElementById('loginLink').style.display='none';
          document.getElementById('registerLink').style.display='none';
          document.getElementById('logoutBtn').style.display='inline-flex';
        }}
      }} catch(_){{
      }}
      document.getElementById('logoutBtn')?.addEventListener('click', async ()=>{{
        try {{ await api.fetch('/api/logout', {{method:'POST'}}); }} catch(_){{
        }}
        api.clearToken();
        location.href='login.html';
      }});
      wireDifficulty();
    }});
  </script>
</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8")

    # --- Service worker for offline practice audio (same behavior as before) ---
    sw_js = """/* practice SW */
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
    const cacheName = data.cache || 'practice-cache';
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
