# app/flashcards.py
import json

from .sets_utils import sanitize_filename
from .constants import PAGES_DIR as DOCS_DIR


def generate_flashcard_html(set_name, data):
    """
    Generates:
      - docs/flashcards/<set_name>/index.html   (learning UI)
      - docs/flashcards/<set_name>/summary.html (results UI)

    This version:
      - Uses per-utterance recognizers (recognizeOnceAsync) with PhraseList bias.
      - Avoids continuous start/stop flicker that can cause iOS mic route changes.
      - Adds ?debug=1 overlay (reasons, cancel details, raw JSON).
      - Keeps audio preloading (current + next).
      - Drops session_state.js include to silence 502 preflight noise.
    """
    output_dir = DOCS_DIR / "flashcards" / set_name
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "index.html"
    summary_path = output_dir / "summary.html"

    # Ensure audio filenames exist in data (keep convention)
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

    /* Debug overlay */
    #dbg {{ display:none; position:fixed; bottom:8px; left:8px; right:8px; max-height:42vh; overflow:auto;
           background:#000; color:#0f0; padding:8px 10px; border-radius:10px; font-family:ui-monospace, SFMono-Regular, Menlo, monospace; font-size:12px; white-space:pre-wrap; }}
    #dbg .row {{ opacity:.9; }}
    #dbg .raw {{ color:#9ef; }}
  </style>
</head>
<body>
  <h1>{set_name} • Learn <button class="home-btn" onclick="goHome()">🏠</button></h1>
  <div class="hint" id="speakHint">Hold the button and speak clearly.</div>

  <div class="card" id="cardContainer" aria-live="polite">
    <div class="card-inner" id="cardInner">
      <div class="side front" id="frontSide">
        <div class="cue" id="frontCue"></div>
        <div class="actions">
          <button class="btn-small" id="btnSayFront" title="Press & hold to speak">🎤 Say it in Polish</button>
        </div>
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
  <!-- NOTE: session_state.js temporarily removed to avoid 502 preflight noise -->
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

    // Scoring + points
    const PASS = 75;
    const tracker = {{ attempts: 0, per: {{}}, perfectNoFlipCount: 0 }};
    let hasFlippedCurrent = false;

    // --- Audio preload cache ---
    const audioCache = new Map(); // index -> HTMLAudioElement

    // --- Debug overlay ---
    const DEBUG = new URL(location.href).searchParams.get('debug') === '1';
    const dbgEl = document.getElementById('dbg');
    if (DEBUG) dbgEl.style.display = 'block';
    function logDbg(...a) {{
      if (!DEBUG) return;
      const line = document.createElement('div'); line.className = 'row';
      line.textContent = a.map(x => (typeof x === 'string' ? x : JSON.stringify(x))).join(' ');
      dbgEl.appendChild(line); dbgEl.scrollTop = dbgEl.scrollHeight;
      try {{ console.debug('[FC]', ...a); }} catch(_) {{}}
    }}
    function logRaw(j) {{
      if (!DEBUG) return;
      const line = document.createElement('div'); line.className = 'row raw';
      line.textContent = (typeof j === 'string') ? j : JSON.stringify(j);
      dbgEl.appendChild(line); dbgEl.scrollTop = dbgEl.scrollHeight;
    }}

    // --- Platform detect ---
    const ua = navigator.userAgent || '';
    const IS_IOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    const IS_SAFARI = /^((?!chrome|android).)*safari/i.test(ua);

    // --- Mic pre-warm (helps Safari) ---
    async function prewarmMic() {{
      try {{
        if (!navigator.mediaDevices?.getUserMedia) return;
        const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
        stream.getTracks().forEach(tr => tr.stop());
        // Nudge AudioContext (helps Safari start without clipping first syllable)
        try {{
          const Ctx = window.AudioContext || window.webkitAudioContext;
          if (Ctx) {{ const ctx = new Ctx(); await ctx.resume(); await new Promise(r => setTimeout(r, 40)); await ctx.close(); }}
        }} catch (_) {{}}
      }} catch (e) {{ logDbg('prewarm error', e && e.message); }}
    }}

    // Mirror of Python sanitize_filename (for audio file names)
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
      const a = new Audio(); a.preload = "auto"; a.src = src;
      try {{ a.load(); }} catch(_e) {{}}
      audioCache.set(index, a);
    }}

    function resetAndPrimeAround(index) {{
      audioCache.clear();
      primeAudio(index); primeAudio(index + 1);
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
      setNavUI(); hasFlippedCurrent = false; resetAndPrimeAround(currentIndex);
    }}

    // ---------------- Azure speech (per-utterance recognizer) ----------------
    async function fetchToken() {{
      try {{
        const tok = await api.get('/api/speech_token', {{ noAuth: true }});
        const token  = tok && (tok.token || tok.access_token);
        const region = tok && (tok.region || tok.location || tok.regionName);
        if (!token || !region) throw new Error('no_token');
        return {{ token, region }};
      }} catch (e) {{ throw new Error('no_token'); }}
    }}

    async function assess(referenceText, targetEl) {{
      const ref = (referenceText || "").trim();
      if (!window.SpeechSDK) {{ targetEl.textContent = "⚠️ Speech SDK not loaded."; return 0; }}
      if (!ref) {{ targetEl.textContent = "⚠️ No reference text."; return 0; }}

      try {{
        targetEl.textContent = "🎤 Preparing…";
        await prewarmMic();
        await new Promise(r => setTimeout(r, 120)); // let UI update

        const {{ token, region }} = await fetchToken();
        const SDK = window.SpeechSDK;

        const speechConfig = SDK.SpeechConfig.fromAuthorizationToken(token, region);
        speechConfig.speechRecognitionLanguage = "pl-PL";
        // Detailed JSON + word timings to ensure PA shows up
        speechConfig.outputFormat = SDK.OutputFormat.Detailed;
        speechConfig.setProperty(SDK.PropertyId.SpeechServiceResponse_RequestDetailedResultTrueFalse, "true");
        speechConfig.setProperty(SDK.PropertyId.SpeechServiceResponse_RequestWordLevelTimestamps, "true");
        // Short utterance: allow a beat to start, end quickly after silence
        speechConfig.setProperty(SDK.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, (IS_IOS || IS_SAFARI) ? "2200" : "1600");
        speechConfig.setProperty(SDK.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "250");

        const audioConfig = SDK.AudioConfig.fromDefaultMicrophoneInput();
        const recognizer = new SDK.SpeechRecognizer(speechConfig, audioConfig);

        // Pronunciation Assessment + Phrase biasing toward the expected word
        const pa = new SDK.PronunciationAssessmentConfig(
          ref,
          SDK.PronunciationAssessmentGradingSystem.HundredMark,
          SDK.PronunciationAssessmentGranularity.Word,
          true /* miscue */
        );
        pa.applyTo(recognizer);
        try {{
          const pl = SDK.PhraseListGrammar.fromRecognizer(recognizer);
          if (pl) pl.add(ref);
        }} catch (_){{

        targetEl.textContent = "🎙 Listening…";

        const result = await new Promise((resolve, reject) => {{
          try {{
            recognizer.recognizeOnceAsync(
              r => resolve(r),
              err => reject(err)
            );
          }} catch (e) {{ reject(e); }}
        }});

        // Log reasons when debugging
        try {{
          logDbg('reason', result?.reason);
          if (result?.reason === SDK.ResultReason.Canceled) {{
            const c = SDK.CancellationDetails.fromResult(result);
            logDbg('canceled', c?.reason, c?.errorCode, c?.errorDetails);
          }}
          if (result?.reason === SDK.ResultReason.NoMatch) {{
            const d = SDK.NoMatchDetails.fromResult(result);
            logDbg('noMatch', d?.reason);
          }}
        }} catch(_){{

        // Parse JSON for PA
        let raw = null;
        try {{
          raw = result?.properties?.getProperty(SDK.PropertyId.SpeechServiceResponse_JsonResult)
             || result?.privPronunciationAssessmentJson
             || result?.privJson; // some builds expose this
        }} catch(_){{

        let score = 0;
        if (raw) {{
          try {{
            const j = JSON.parse(raw);
            logRaw(j);
            score = Math.round(
              (j?.NBest?.[0]?.PronunciationAssessment?.AccuracyScore) ??
              (j?.PronunciationAssessment?.AccuracyScore) ?? 0
            );
          }} catch(_){{
            // ignore JSON parse error
          }}
        }}

        try {{ recognizer.close(); }} catch(_){{

        targetEl.textContent = score ? `✅ ${{score}}%` : "⚠️ No score";
        return score || 0;

      }} catch (e) {{
        const msg = (e && e.message) || String(e);
        logDbg('assess error', msg);
        targetEl.textContent = (msg === "no_token") ? "⚠️ Token issue" : "⚠️ Speech error";
        return 0;
      }}
    }}

    // ---------- UI wiring ----------
    window.addEventListener("DOMContentLoaded", async function() {{
      // Hint line
      document.getElementById('speakHint').textContent =
        (IS_IOS || IS_SAFARI) ? "Hold the button while you speak." : "Click, then speak.";

      // Try to load R2 manifest (non-blocking)
      try {{ if (window.AudioPaths) r2Manifest = await AudioPaths.fetchManifest(setName); }} catch (_e) {{ r2Manifest = null; }}

      renderCard();

      // Flip on tap (ignore buttons/result)
      document.getElementById("cardContainer").addEventListener("click", (e) => {{
        if (e.target.closest("button") || e.target.classList.contains("result")) return;
        document.getElementById("cardContainer").classList.toggle("flipped");
        hasFlippedCurrent = true;
      }});

      // ---- Front: Say it  (press & hold UX; technically single-shot underneath) ----
      const sayBtn = document.getElementById("btnSayFront");
      const frontRes = document.getElementById("frontResult");
      const getRef = () => (cards[currentIndex] && cards[currentIndex].phrase) || "";

      // Press & hold visuals; we kick off recognizeOnce on press.
      const startSpeak = async () => {{
        const ref = getRef();
        if (!ref.trim()) {{ frontRes.textContent = "⚠️ No reference text."; return; }}
        sayBtn.disabled = true;
        const s = await assess(ref, frontRes);
        // record stats
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
      }};

      // pointer/touch (we don't cancel on release; recognizeOnce ends on silence)
      sayBtn.addEventListener('pointerdown', (ev) => {{ ev.preventDefault(); startSpeak(); }});
      sayBtn.addEventListener('touchstart',  (ev) => {{ ev.preventDefault(); startSpeak(); }}, {{passive:false}});
      // Desktop click fallback
      sayBtn.addEventListener("click", (e) => {{ e.stopPropagation(); startSpeak(); }});

      // ---- Back: Play (preloaded)
      document.getElementById("btnPlay").addEventListener("click", async (e) => {{
        e.stopPropagation();
        let a = audioCache.get(currentIndex);
        if (!a) {{ primeAudio(currentIndex); a = audioCache.get(currentIndex); }}
        if (a) {{ try {{ a.currentTime = 0; }} catch(_){{}} a.play().catch(err => logDbg('audio play err', err?.message || err)); }}
      }});

      // Prev / Next / Finish
      document.getElementById("prevBtn").addEventListener("click", () => {{
        if (currentIndex > 0) {{
          currentIndex--;
          renderCard();
          // (SessionSync disabled while session_state CORS is noisy)
        }}
      }});

      document.getElementById("nextBtn").addEventListener("click", async () => {{
        if (currentIndex < cards.length - 1) {{
          currentIndex++;
          renderCard();
        }} else {{
          // FINISH
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

          const q = awarded != null ? ("?awarded=" + encodeURIComponent(awarded)) : "";
          window.location.href = "summary.html" + q;
        }}
      }});

      // Load audio manifest last
      try {{ if (window.AudioPaths) r2Manifest = await AudioPaths.fetchManifest(setName); }} catch(_e) {{}}
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
      }} catch (_) {{}}

      if (!done) {{
        try {{
          const raw = localStorage.getItem('lp_last_result_' + setName);
          if (raw) {{
            const j = JSON.parse(raw);
            apply(Math.round(Number(j.score)||0), Number(j.attempts)||0, Number(j.total)||undefined, Number(j.points_total)||undefined, awarded);
            done = true;
          }}
        }} catch(_) {{}}
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
