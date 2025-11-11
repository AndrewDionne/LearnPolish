# app/flashcards.py
import json

from .sets_utils import sanitize_filename
from .constants import PAGES_DIR as DOCS_DIR


def generate_flashcard_html(set_name, data):
    """
    Generates:
      - docs/flashcards/<set_name>/index.html   (learning UI, capture-first)
      - docs/flashcards/<set_name>/summary.html (results UI)

    Capture-first recognizer:
      - Click once → records ~2.5s → streams PCM to Azure → returns score
      - Tiny level meter while recording
      - Uses /api/speech_token for Azure auth
      - Audio preloads (current + next)

    URL switches:
      - ?debug=1     → show debug overlay (reason/raw JSON)
      - ?live=1      → force live mic (recognizeOnce on default mic)
      - ?capture=0/1 → force capture off/on (default is capture)
    """
    output_dir = DOCS_DIR / "flashcards" / set_name
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "index.html"
    summary_path = output_dir / "summary.html"

    # Ensure audio filenames exist in data
    for idx, entry in enumerate(data):
        try:
            entry["audio_file"] = f"{idx}_{sanitize_filename(entry.get('phrase', ''))}.mp3"
        except Exception:
            entry["audio_file"] = f"{idx}_.mp3"

    cards_json = json.dumps(data, ensure_ascii=False).replace(r"</", r"<\/")

    # --------- LEARN PAGE (index.html) ----------
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{set_name} • Learn</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="icon" type="image/svg+xml" href="../../static/brand.svg" />
  <style>
    body {{ font-family: -apple-system,BlinkMacSystemFont, sans-serif; margin:0; padding:20px; background:#f8f9fa; display:flex; flex-direction:column; align-items:center; min-height:100vh; }}
    h1 {{ font-size:1.5em; margin:0 0 8px; position:relative; width:100%; text-align:center; }}
    .home-btn {{ position:absolute; right:0; top:0; font-size:1.4em; background:none; border:none; cursor:pointer; }}

    .hint {{ color:#5a6472; font-size:.9em; margin-bottom:8px; }}

    .card {{ width:90%; max-width:360px; height:260px; perspective:1000px; margin:12px auto; }}
    .card-inner {{
      width:100%; height:100%; position:relative; transition:transform .6s; transform-style:preserve-3d;
      cursor:pointer; box-shadow:0 4px 10px rgba(0,0,0,.1); display:flex; justify-content:center; align-items:center; border-radius:12px;
    }}
    .card.flipped .card-inner {{ transform: rotateY(180deg); }}
    .side {{ position:absolute; width:100%; height:100%; border-radius:12px; padding:20px; backface-visibility:hidden; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; }}
    .front {{ background:#fff; }}
    .back  {{ background:#e9ecef; transform:rotateY(180deg); }}

    .cue {{ font-size:1.1em; margin-bottom:12px; }}
    .answer-phrase {{ font-weight:700; font-size:1.2em; }}
    .answer-pron {{ font-style:italic; margin-top:4px; }}

    .actions {{ display:flex; gap:8px; margin-top:16px; }}
    .btn-small {{ padding:10px 14px; font-size:1em; background:#2d6cdf; color:#fff; border:none; border-radius:10px; cursor:pointer; }}
    .btn-green {{ background:#28a745; }}

    .result {{ margin-top:8px; font-size:.95em; min-height:1.2em; }}

    .nav-buttons {{ display:flex; gap:12px; margin-top:16px; }}
    .nav-button {{ padding:10px 14px; font-size:1em; background:#007bff; color:#fff; border:none; border-radius:10px; min-width:110px; cursor:pointer; }}
    .nav-button:disabled {{ background:#aaa; cursor:default; }}

    /* Debug overlay (only shows when ?debug=1) */
    #dbg {{ display:none; position:fixed; bottom:8px; left:8px; right:8px; max-height:46vh; overflow:auto;
           background:#000; color:#0f0; padding:8px 10px; border-radius:10px; font-family:ui-monospace, SFMono-Regular, Menlo, monospace; font-size:12px; white-space:pre-wrap; z-index:9999; }}
    #dbg .row {{ opacity:.95; }}
    #dbg .raw {{ color:#9ef; }}

    /* Tiny level meter (capture mode) */
    #meterWrap {{ display:none; margin-top:10px; width:260px; height:8px; background:#e6e6ef; border-radius:6px; overflow:hidden; }}
    #meterBar {{ width:0%; height:100%; background:#2d6cdf; }}
    #dlWav {{ display:none; margin-top:8px; }}
  </style>
</head>
<body>
  <h1>{set_name} • Learn <button class="home-btn" onclick="goHome()">🏠</button></h1>
  <div class="hint" id="speakHint">Tap to record, then we’ll score it.</div>

  <div class="card" id="cardContainer" aria-live="polite">
    <div class="card-inner" id="cardInner">
      <div class="side front" id="frontSide">
        <div class="cue" id="frontCue"></div>
        <div class="actions">
          <button class="btn-small" id="btnSayFront" title="Record then score">🎤 Say it in Polish</button>
        </div>
        <div id="meterWrap"><div id="meterBar"></div></div>
        <a id="dlWav" class="btn-small" download="capture.wav">⬇️ Download last capture</a>
        <div class="result" id="frontResult"></div>
      </div>
      <div class="side back" id="backSide">
        <div class="answer-phrase" id="answerPhrase"></div>
        <div class="answer-pron" id="answerPron"></div>
        <div class="actions">
          <button class="btn-small btn-green" id="btnPlay">🔊 Play</button>
        </div>
        <div class="result" id="backResult"></div>
      </div>
    </div>
  </div>

  <div class="nav-buttons">
    <button id="prevBtn" class="nav-button">Previous</button>
    <button id="nextBtn" class="nav-button">Next</button>
  </div>

  <div id="dbg"></div>

  <!-- Scripts -->
  <script src="../../static/js/app-config.js"></script>
  <script src="../../static/js/api.js"></script>
  <!-- session_state.js intentionally omitted to avoid races -->
  <script src="../../static/js/audio-paths.js"></script>
  <!-- Azure Speech SDK -->
  <script src="https://aka.ms/csspeech/jsbrowserpackageraw"></script>

  <script>
    // --- Data & state ---
    const cards = {cards_json};
    const setName = "{set_name}";
    const mode = "flashcards";
    let currentIndex = 0;

    // Optional CDN manifest
    let r2Manifest = null;

    // Debug overlay
    const DEBUG = new URL(location.href).searchParams.get('debug') === '1';
    const dbgEl = document.getElementById('dbg');
    if (DEBUG) dbgEl.style.display = 'block';
    function logDbg(...a) {{
      if (!DEBUG) return;
      const line = document.createElement('div');
      line.className = 'row';
      line.textContent = a.map(x => (typeof x === 'string' ? x : JSON.stringify(x))).join(' ');
      dbgEl.appendChild(line);
      dbgEl.scrollTop = dbgEl.scrollHeight;
      try {{ console.debug('[FC]', ...a); }} catch(_) {{}}
    }}
    function logRaw(j) {{
      if (!DEBUG) return;
      const line = document.createElement('div');
      line.className = 'row raw';
      line.textContent = (typeof j === 'string') ? j : JSON.stringify(j);
      dbgEl.appendChild(line);
      dbgEl.scrollTop = dbgEl.scrollHeight;
    }}

    // URL overrides (default capture)
    const URLP = new URL(location.href).searchParams;
    const FORCE_LIVE = URLP.get('live') === '1';
    const capQ = URLP.get('capture');
    const CAPTURE_MODE = FORCE_LIVE ? false : (capQ === '0' ? false : true);

    // Scoring + points
    const PASS = 75;
    const tracker = {{ attempts: 0, per: {{}}, perfectNoFlipCount: 0 }};
    let hasFlippedCurrent = false;

    // Audio preload cache
    const audioCache = new Map();

    // Platform text
    const ua = navigator.userAgent || '';
    const IS_IOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    const IS_SAFARI = /^((?!chrome|android).)*safari/i.test(ua);
    document.getElementById('speakHint').textContent =
      CAPTURE_MODE ? "Tap to record, then we’ll score it." :
      (IS_IOS || IS_SAFARI) ? "Tap, then speak." : "Click, then speak.";

    // Mic prewarm (helps Safari start cleanly)
    async function prewarmMic() {{
      try {{
        if (!navigator.mediaDevices?.getUserMedia) return;
        const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
        stream.getTracks().forEach(tr => tr.stop());
        try {{
          const Ctx = window.AudioContext || window.webkitAudioContext;
          if (Ctx) {{ const ctx = new Ctx(); await ctx.resume(); await new Promise(r => setTimeout(r, 40)); await ctx.close(); }}
        }} catch (_e) {{}}
      }} catch (e) {{
        logDbg('prewarm error', e && e.message);
      }}
    }}

    // Filename helper (mirror Python sanitize)
    function sanitizeFilename(text) {{
      return (text || "")
        .normalize("NFD").replace(/[\\u0300-\\u036f]/g, "")
        .replace(/[^a-zA-Z0-9_-]+/g, "_").replace(/^_+|_+$/g, "");
    }}

    function localAudioPath(index) {{
      const e = cards[index] || {{}};
      const fn = String(index) + "_" + sanitizeFilename(e.phrase || "") + ".mp3";
      const setEnc = encodeURIComponent(setName);
      const fnEnc  = encodeURIComponent(fn);
      const explicit = e.audio_url || e.audio;
      if (explicit && /^https?:\\/\\//i.test(explicit)) return explicit;
      return `../../static/${{setEnc}}/audio/${{fnEnc}}`;
    }}

    function buildAudioSrc(index) {{
      let src = localAudioPath(index);
      try {{ if (window.AudioPaths) src = AudioPaths.buildAudioPath(setName, index, cards[index], r2Manifest); }} catch (_ignore) {{}}
      return src;
    }}

    function primeAudio(index) {{
      if (index < 0 || index >= cards.length) return;
      if (audioCache.has(index)) return;
      const src = buildAudioSrc(index);
      const a = new Audio();
      a.preload = "auto";
      a.src = src;
      try {{ a.load(); }} catch(_e) {{}}
      audioCache.set(index, a);
    }}

    function resetAndPrimeAround(index) {{
      audioCache.clear();
      primeAudio(index);
      primeAudio(index + 1);
    }}

    function setNavUI() {{
      document.getElementById("prevBtn").disabled = (currentIndex === 0);
      const nextBtn = document.getElementById("nextBtn");
      nextBtn.textContent = (currentIndex < cards.length - 1) ? "Next" : "Finish";
    }}

    function renderCard() {{
      const e = cards[currentIndex] || {{}};
      document.getElementById("frontCue").textContent = e.meaning || "";
      document.getElementById("frontResult").textContent = "";
      document.getElementById("answerPhrase").textContent = e.phrase || "";
      document.getElementById("answerPron").textContent   = e.pronunciation || "";
      document.getElementById("backResult").textContent   = "";
      setNavUI();
      hasFlippedCurrent = false;
      resetAndPrimeAround(currentIndex);
    }}

    // --------------- Token fetch ----------------
    async function fetchToken() {{
      try {{
        const tok = await api.get('/api/speech_token', {{ noAuth: true }});
        const token  = tok && (tok.token || tok.access_token);
        const region = tok && (tok.region || tok.location || tok.regionName);
        if (!token || !region) throw new Error('no_token_or_region');
        logDbg('SDK?', !!window.SpeechSDK, 'region', region, 'tok', !!token);
        return {{ token, region }};
      }} catch (e) {{
        logDbg('token fetch error', e?.message || e);
        return {{ token: null, region: null }};
      }}
    }}

    // --------------- Capture-first path ----------------
    const meterWrap = document.getElementById('meterWrap');
    const meterBar  = document.getElementById('meterBar');
    const dlWav     = document.getElementById('dlWav');

    async function recordBlob(ms=2500) {{
      meterWrap.style.display = CAPTURE_MODE ? 'block' : 'none';
      let mediaStream = null;
      let mediaRec = null;
      let chunks = [];
      let meterTimer = null;
      try {{
        mediaStream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
        // Level meter
        try {{
          const ACtx = window.AudioContext || window.webkitAudioContext;
          if (ACtx) {{
            const ctx = new ACtx();
            const src = ctx.createMediaStreamSource(mediaStream);
            const analyser = ctx.createAnalyser();
            analyser.fftSize = 2048;
            src.connect(analyser);
            const data = new Uint8Array(analyser.fftSize);
            meterTimer = setInterval(() => {{
              analyser.getByteTimeDomainData(data);
              let sum = 0; for (let i=0; i<data.length; i++) {{ const v=(data[i]-128)/128; sum += v*v; }}
              const rms = Math.sqrt(sum/data.length);
              const pct = Math.min(100, Math.round(rms*180));
              meterBar.style.width = pct + '%';
            }}, 60);
          }}
        }} catch(_ignore) {{}}

        mediaRec = new MediaRecorder(mediaStream, {{ mimeType: 'audio/webm' }});
        mediaRec.ondataavailable = e => {{ if (e.data && e.data.size) chunks.push(e.data); }};
        mediaRec.start();
        await new Promise(r => setTimeout(r, ms));
        mediaRec.stop();
        await new Promise(r => mediaRec.onstop = r);
        return new Blob(chunks, {{ type: 'audio/webm' }});
      }} finally {{
        try {{ if (meterTimer) clearInterval(meterTimer); }} catch(_ignore) {{}}
        try {{ meterBar.style.width = '0%'; }} catch(_ignore) {{}}
        try {{ mediaStream && mediaStream.getTracks().forEach(t => t.stop()); }} catch(_ignore) {{}}
        meterWrap.style.display = 'none';
      }}
    }}

    async function blobToPCM16Mono(blob, targetRate=16000) {{
      const arr = await blob.arrayBuffer();
      const ACtx = window.AudioContext || window.webkitAudioContext;
      if (!ACtx) throw new Error('no_audiocontext');
      const ctx = new ACtx();
      const buf = await ctx.decodeAudioData(arr.slice(0));
      // Downmix mono
      const chL = buf.getChannelData(0);
      let mono;
      if (buf.numberOfChannels > 1) {{
        const chR = buf.getChannelData(1);
        mono = new Float32Array(buf.length);
        for (let i=0;i<buf.length;i++) mono[i] = 0.5*(chL[i] + chR[i]);
      }} else {{
        mono = chL;
      }}
      // Linear resample
      const ratio = buf.sampleRate / targetRate;
      const outLen = Math.round(mono.length / ratio);
      const out = new Float32Array(outLen);
      for (let i=0;i<outLen;i++) {{
        const idx = i * ratio;
        const i0 = Math.floor(idx);
        const i1 = Math.min(i0+1, mono.length-1);
        const frac = idx - i0;
        out[i] = mono[i0]*(1-frac) + mono[i1]*frac;
      }}
      // Float32 -> Int16LE
      const pcm = new Int16Array(outLen);
      for (let i=0;i<outLen;i++) {{
        let v = Math.max(-1, Math.min(1, out[i]));
        pcm[i] = v < 0 ? v * 0x8000 : v * 0x7FFF;
      }}
      try {{ ctx.close(); }} catch(_ignore) {{}}
      return pcm;
    }}

    function pcmToWavBlob(pcm, sampleRate=16000) {{
      const numFrames = pcm.length;
      const bytesPerSample = 2;
      const blockAlign = 1 * bytesPerSample;
      const byteRate = sampleRate * blockAlign;
      const dataSize = numFrames * bytesPerSample;
      const buf = new ArrayBuffer(44 + dataSize);
      const v = new DataView(buf);
      let o = 0;
      function wstr(s) {{ for (let i=0;i<s.length;i++) v.setUint8(o++, s.charCodeAt(i)); }}
      function wu16(x) {{ v.setUint16(o, x, true); o+=2; }}
      function wu32(x) {{ v.setUint32(o, x, true); o+=4; }}
      wstr('RIFF'); wu32(36 + dataSize); wstr('WAVE');
      wstr('fmt '); wu32(16); wu16(1); wu16(1); wu32(sampleRate); wu32(byteRate); wu16(blockAlign); wu16(16);
      wstr('data'); wu32(dataSize);
      for (let i=0;i<pcm.length;i++) v.setInt16(o + i*2, pcm[i], true);
      return new Blob([v], {{ type: 'audio/wav' }});
    }}

    function extractScore(result, SDK) {{
      try {{
        const pa = SDK.PronunciationAssessmentResult.fromResult(result);
        if (pa && Number.isFinite(pa.accuracyScore)) return Math.round(pa.accuracyScore);
      }} catch(_ignore) {{}}
      // Fallback JSON parse
      let raw = null;
      try {{
        raw = result?.properties?.getProperty(SDK.PropertyId.SpeechServiceResponse_JsonResult)
           || result?.privPronunciationAssessmentJson
           || result?.privJson;
      }} catch(_ignore) {{}}
      if (raw) {{
        try {{
          const j = JSON.parse(raw);
          const acc = (j?.NBest?.[0]?.PronunciationAssessment?.AccuracyScore) ??
                      (j?.PronunciationAssessment?.AccuracyScore) ?? 0;
          return Math.round(Number(acc) || 0);
        }} catch(_ignore) {{}}
      }}
      return 0;
    }}

    async function assessCapture(referenceText, targetEl) {{
      const ref = (referenceText || "").trim();
      if (!window.SpeechSDK) {{ targetEl.textContent = "⚠️ SDK not loaded."; return 0; }}
      if (!ref) {{ targetEl.textContent = "⚠️ No reference text."; return 0; }}

      targetEl.textContent = "🎤 Recording…";
      const blob = await recordBlob(2500);

      const {{ token, region }} = await fetchToken();
      if (!token || !region) {{ targetEl.textContent = "⚠️ Token/region issue"; return 0; }}

      const SDK = window.SpeechSDK;
      const speechConfig = SDK.SpeechConfig.fromAuthorizationToken(token, region);
      speechConfig.speechRecognitionLanguage = "pl-PL";
      speechConfig.outputFormat = SDK.OutputFormat.Detailed;
      speechConfig.setProperty(SDK.PropertyId.SpeechServiceResponse_RequestDetailedResultTrueFalse, "true");
      speechConfig.setProperty(SDK.PropertyId.SpeechServiceResponse_RequestWordLevelTimestamps, "true");
      // IMPORTANT: Do NOT set EndSilenceTimeout on push-stream capture; it can suppress PA payloads.

      // Push 16k/16-bit/mono PCM
      const pcm = await blobToPCM16Mono(blob, 16000);
      const format = SDK.AudioStreamFormat.getWaveFormatPCM(16000, 16, 1);
      const push = SDK.AudioInputStream.createPushStream(format);
      push.write(new Uint8Array(pcm.buffer));
      push.close();

      const audioConfig = SDK.AudioConfig.fromStreamInput(push);
      const recognizer = new SDK.SpeechRecognizer(speechConfig, audioConfig);

      // Pronunciation Assessment + phrase bias
      const pa = new SDK.PronunciationAssessmentConfig(
        ref,
        SDK.PronunciationAssessmentGradingSystem.HundredMark,
        SDK.PronunciationAssessmentGranularity.Word,
        true
      );
      pa.applyTo(recognizer);
      try {{
        const pl = SDK.PhraseListGrammar.fromRecognizer(recognizer);
        if (pl) pl.add(ref);
      }} catch (_ignore) {{}}

      targetEl.textContent = "🧠 Scoring…";

      const result = await new Promise((resolve, reject) => {{
        try {{ recognizer.recognizeOnceAsync(resolve, reject); }}
        catch (e) {{ reject(e); }}
      }}).catch(e => {{ logDbg('recognizeOnce(push) error', e?.message || e); return null; }});

      try {{ recognizer.close(); }} catch(_ignore) {{}}

      if (!result) {{ targetEl.textContent = "⚠️ Speech error"; return 0; }}

      // Optional debug details
      try {{
        logDbg('reason', result?.reason);
        const SDKR = window.SpeechSDK;
        if (result?.reason === SDKR.ResultReason.Canceled) {{
          const c = SDKR.CancellationDetails.fromResult(result);
          logDbg('canceled', c?.reason, c?.errorCode, c?.errorDetails);
        }}
        if (result?.reason === SDKR.ResultReason.NoMatch) {{
          const d = SDKR.NoMatchDetails.fromResult(result);
          logDbg('noMatch', d?.reason);
        }}
        const raw = result?.properties?.getProperty(SDK.PropertyId.SpeechServiceResponse_JsonResult)
                 || result?.privPronunciationAssessmentJson || result?.privJson;
        if (raw) try {{ logRaw(JSON.parse(raw)); }} catch(_ignore) {{ logRaw(raw); }}
      }} catch(_ignore) {{}}

      const score = extractScore(result, SDK);
      targetEl.textContent = score ? `✅ ${{score}}%` : "⚠️ No score";
      return score || 0;
    }}

    // Optional live path (only if forced via ?live=1 or ?capture=0)
    async function assessLive(referenceText, targetEl) {{
      const ref = (referenceText || "").trim();
      if (!window.SpeechSDK) {{ targetEl.textContent = "⚠️ SDK not loaded."; return 0; }}
      if (!ref) {{ targetEl.textContent = "⚠️ No reference text."; return 0; }}
      targetEl.textContent = "🎤 Preparing…";
      await prewarmMic();
      await new Promise(r => setTimeout(r, 120));

      const {{ token, region }} = await fetchToken();
      if (!token || !region) {{ targetEl.textContent = "⚠️ Token/region issue"; return 0; }}

      const SDK = window.SpeechSDK;
      const speechConfig = SDK.SpeechConfig.fromAuthorizationToken(token, region);
      speechConfig.speechRecognitionLanguage = "pl-PL";
      speechConfig.outputFormat = SDK.OutputFormat.Detailed;
      speechConfig.setProperty(SDK.PropertyId.SpeechServiceResponse_RequestDetailedResultTrueFalse, "true");
      speechConfig.setProperty(SDK.PropertyId.SpeechServiceResponse_RequestWordLevelTimestamps, "true");
      speechConfig.setProperty(SDK.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, (IS_IOS || IS_SAFARI) ? "2200" : "1600");
      speechConfig.setProperty(SDK.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "250");

      const audioConfig = SDK.AudioConfig.fromDefaultMicrophoneInput();
      const recognizer = new SDK.SpeechRecognizer(speechConfig, audioConfig);

      const pa = new SDK.PronunciationAssessmentConfig(
        ref,
        SDK.PronunciationAssessmentGradingSystem.HundredMark,
        SDK.PronunciationAssessmentGranularity.Word,
        true
      );
      pa.applyTo(recognizer);
      try {{
        const pl = SDK.PhraseListGrammar.fromRecognizer(recognizer);
        if (pl) pl.add(ref);
      }} catch (_ignore) {{}}

      targetEl.textContent = "🎙 Listening…";

      const result = await new Promise((resolve, reject) => {{
        try {{ recognizer.recognizeOnceAsync(resolve, reject); }}
        catch (e) {{ reject(e); }}
      }}).catch(e => {{ logDbg('recognizeOnce(live) error', e?.message || e); return null; }});

      try {{ recognizer.close(); }} catch(_ignore) {{}}

      if (!result) {{ targetEl.textContent = "⚠️ Speech error"; return 0; }}

      // Optional debug details
      try {{
        logDbg('reason', result?.reason);
        const SDKR = window.SpeechSDK;
        if (result?.reason === SDKR.ResultReason.Canceled) {{
          const c = SDKR.CancellationDetails.fromResult(result);
          logDbg('canceled', c?.reason, c?.errorCode, c?.errorDetails);
        }}
        if (result?.reason === SDKR.ResultReason.NoMatch) {{
          const d = SDKR.NoMatchDetails.fromResult(result);
          logDbg('noMatch', d?.reason);
        }}
        const raw = result?.properties?.getProperty(SDK.PropertyId.SpeechServiceResponse_JsonResult)
                 || result?.privPronunciationAssessmentJson || result?.privJson;
        if (raw) try {{ logRaw(JSON.parse(raw)); }} catch(_ignore) {{ logRaw(raw); }}
      }} catch(_ignore) {{}}

      const score = extractScore(result, SDK);
      targetEl.textContent = score ? `✅ ${{score}}%` : "⚠️ No score";
      return score || 0;
    }}

    // ---------- UI wiring ----------
    window.addEventListener("DOMContentLoaded", async function() {{
      try {{ if (window.AudioPaths) r2Manifest = await AudioPaths.fetchManifest(setName); }} catch (_ignore) {{ r2Manifest = null; }}
      try {{ logDbg('SDK version?', window.SpeechSDK?.Version || 'unknown'); }} catch(_ignore) {{}}

      renderCard();

      // Flip on tap (ignore buttons/result)
      document.getElementById("cardContainer").addEventListener("click", (e) => {{
        if (e.target.closest("button") || e.target.classList.contains("result")) return;
        document.getElementById("cardContainer").classList.toggle("flipped");
        hasFlippedCurrent = true;
      }});

      // Front: Say it (capture-first, optional live if forced)
      const sayBtn = document.getElementById("btnSayFront");
      const frontRes = document.getElementById("frontResult");
      const getRef = () => (cards[currentIndex] && cards[currentIndex].phrase) || "";

      sayBtn.addEventListener("click", async (e) => {{
        e.stopPropagation();
        const ref = getRef();
        if (!ref.trim()) {{ frontRes.textContent = "⚠️ No reference text."; return; }}
        sayBtn.disabled = true;
        const s = CAPTURE_MODE ? await assessCapture(ref, frontRes) : await assessLive(ref, frontRes);
        tracker.attempts++;
        if (!tracker.per[currentIndex]) tracker.per[currentIndex] = {{ tries: 0, best: 0, got100BeforeFlip: false }};
        const r = tracker.per[currentIndex];
        r.tries++;
        if (Number.isFinite(s)) {{
          r.best = Math.max(r.best || 0, s);
          if (!hasFlippedCurrent && s === 100 && !r.got100BeforeFlip) {{
            r.got100BeforeFlip = true; tracker.perfectNoFlipCount++;
          }}
        }}
        sayBtn.disabled = false;
      }});

      // Back: Play (preloaded)
      document.getElementById("btnPlay").addEventListener("click", async (e) => {{
        e.stopPropagation();
        let a = audioCache.get(currentIndex);
        if (!a) {{ primeAudio(currentIndex); a = audioCache.get(currentIndex); }}
        if (a) {{
          try {{ a.currentTime = 0; }} catch(_ignore) {{}}
          a.play().catch(err => logDbg('audio play err', err?.message || err));
        }}
      }});

      // Prev / Next / Finish
      document.getElementById("prevBtn").addEventListener("click", () => {{
        if (currentIndex > 0) {{
          currentIndex--;
          renderCard();
          if (window.SessionSync) SessionSync.save({{ setName, mode, progress: {{ index: currentIndex, per: tracker.per }} }});
        }}
      }});

      document.getElementById("nextBtn").addEventListener("click", async () => {{
        if (currentIndex < cards.length - 1) {{
          currentIndex++;
          renderCard();
          if (window.SessionSync) SessionSync.save({{ setName, mode, progress: {{ index: currentIndex, per: tracker.per }} }});
        }} else {{
          const totalCards = Math.max(1, cards.length);
          const correct = Object.values(tracker.per).filter(r => (r?.best || 0) >= PASS).length;
          const scorePct = Math.round((correct / totalCards) * 100);

          let pointsTotal = 10 + tracker.perfectNoFlipCount;
          if (scorePct === 100) pointsTotal = pointsTotal * 2;

          try {{
            localStorage.setItem("lp_last_result_" + setName, JSON.stringify({{
              score: scorePct, attempts: tracker.attempts, total: totalCards,
              points_total: pointsTotal, perfect_before_flip: tracker.perfectNoFlipCount
            }}));
          }} catch (_ignore) {{}}

          let awarded = null;
          try {{
            const resp = await api.fetch("/api/submit_score", {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify({{
                set_name: setName, mode: "flashcards", score: scorePct, attempts: tracker.attempts,
                details: {{ per: tracker.per, total: totalCards, perfect_before_flip: tracker.perfectNoFlipCount, points_total: pointsTotal }}
              }})
            }});
            if (resp.ok) {{
              const js = await resp.json();
              awarded = (js && js.details && js.details.points_awarded != null) ? Number(js.details.points_awarded) : null;
            }}
          }} catch (_ignore) {{}}

          try {{ if (window.SessionSync) await SessionSync.complete({{ setName, mode }}); }} catch(_ignore) {{}}
          try {{ localStorage.removeItem("lp_last"); }} catch(_ignore) {{}}
          const q = awarded != null ? ("?awarded=" + encodeURIComponent(awarded)) : "";
          window.location.href = "summary.html" + q;
        }}
      }});

      // Optional resume
      (async () => {{
        const wantResume = new URL(location.href).searchParams.get("resume") === "1";
        if (wantResume && window.SessionSync) {{
          await SessionSync.restore({{ setName, mode }}, (progress) => {{
            if (progress && Number.isFinite(progress.index)) {{
              currentIndex = Math.max(0, Math.min(cards.length - 1, progress.index));
            }}
            if (progress && progress.per) Object.assign(tracker.per, progress.per);
            renderCard();
          }});
        }}
        try {{ localStorage.setItem("lp_last", JSON.stringify({{ set_name:setName, mode, ts: Date.now() }})); }} catch(_ignore) {{}}
      }})();
    }});

    function goHome() {{ window.location.href = "../../index.html"; }}
  </script>

</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8")

    # --------- SUMMARY PAGE (summary.html) ----------
    summary_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{set_name} • Results</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="icon" type="image/svg+xml" href="../../static/brand.svg" />

  <style>
    body {{ font-family: -apple-system,BlinkMacSystemFont, sans-serif; margin:0; padding:24px; background:#f8f9fa; display:flex; justify-content:center; }}
    .card {{ background:#fff; border:1px solid #e6e6ef; border-radius:12px; padding:20px; box-shadow:0 1px 2px rgba(8,15,52,.04); width:100%; max-width:560px; }}
    h1 {{ margin-top:0; font-size:22px; }}
    .row {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:14px; }}
    .btn {{ display:inline-block; padding:10px 12px; border-radius:10px; border:1px solid #cfd3e6; background:#fff; text-decoration:none; color:#222; }}
    .btn-primary {{ background:#2d6cdf; border-color:#2d6cdf; color:#fff; }}
    .muted {{ color:#666; }}
    .big {{ font-size:32px; font-weight:700; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>See how you did</h1>
    <div id="resultLine" class="big">Loading…</div>
    <div id="detailLine" class="muted" style="margin-top:6px;"></div>

    <div class="row" style="margin-top:16px;">
      <a id="retryBtn" class="btn btn-primary" href="./">Try again</a>
      <a class="btn" href="../../learn.html">Back to Learn</a>
      <a class="btn" href="../../index.html">Home</a>
    </div>
  </div>

  <script src="../../static/js/api.js"></script>
  <script>
    const setName = "{set_name}";

    function apply(score, attempts, total, pointsTotal, awarded) {{
      document.getElementById('resultLine').textContent = score + '%';
      let tail = (attempts||0) + ' attempts • ' + (total||'?') + ' cards';
      if (pointsTotal != null) tail += ' • ' + pointsTotal + ' pts';
      if (awarded != null)     tail += ' (+' + awarded + ')';
      document.getElementById('detailLine').textContent = tail;
    }}

    (async () => {{
      const urlAwarded = (() => {{
        const v = new URL(location.href).searchParams.get('awarded');
        return (v != null) ? Number(v) : null;
      }})();

      let done = false, awarded = urlAwarded;

      try {{
        let r = await api.fetch('/api/my/scores?limit=1&set_name=' + encodeURIComponent(setName));
        if (!r.ok) r = await api.fetch('/api/get_scores?set_name=' + encodeURIComponent(setName) + '&limit=1');
        if (r.ok) {{
          const payload = await r.json();
          const last = Array.isArray(payload) ? payload[0] : (payload && Array.isArray(payload.scores) ? payload.scores[0] : null);
          if (last && (last.set_name === setName || !last.set_name)) {{
            const d = last.details || {{}};
            if (awarded == null && d.points_awarded != null) awarded = Number(d.points_awarded);
            apply(Math.round(Number(last.score) || 0), Number(last.attempts) || 0, Number(d.total) || undefined, Number(d.points_total) || undefined, awarded);
            done = true;
          }}
        }}
      }} catch (_ignore) {{ }}

      if (!done) {{
        try {{
          const raw = localStorage.getItem('lp_last_result_' + setName);
          if (raw) {{
            const j = JSON.parse(raw);
            apply(Math.round(Number(j.score)||0), Number(j.attempts)||0, Number(j.total)||undefined, Number(j.points_total)||undefined, awarded);
            done = true;
          }}
        }} catch(_ignore) {{ }}
      }}

      if (!done) {{
        document.getElementById('resultLine').textContent = '—';
        document.getElementById('detailLine').textContent = 'No recent result found.';
      }}
    }})();
  </script>
</body>
</html>
"""
    summary_path.write_text(summary_html, encoding="utf-8")

    print(f"✅ flashcards pages generated: {out_path} and {summary_path}")
    return out_path
