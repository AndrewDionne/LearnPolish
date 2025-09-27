# app/flashcards.py
import json
from pathlib import Path

from .sets_utils import sanitize_filename

DOCS_DIR = Path("docs")

def generate_flashcard_html(set_name, data):
    """
    Generates:
      - docs/flashcards/<set_name>/index.html   (learning UI)
      - docs/flashcards/<set_name>/summary.html (results UI)

    - TRUE FLIP: Front has “Say it in Polish”; Back has ONLY “Play”.
    - Finish: computes score + points, POSTs /api/submit_score, clears session, -> summary.html
    - Resume mid-set via SessionSync.
    - Correct relative paths for nested pages.
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

    cards_json = json.dumps(data, ensure_ascii=False)

    # --------- LEARN PAGE (index.html) ----------
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{set_name} • Learn</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    body {{ font-family: -apple-system,BlinkMacSystemFont, sans-serif; margin:0; padding:20px; background:#f8f9fa; display:flex; flex-direction:column; align-items:center; min-height:100vh; }}
    h1 {{ font-size:1.5em; margin:0 0 16px; position:relative; width:100%; text-align:center; }}
    .home-btn {{ position:absolute; right:0; top:0; font-size:1.4em; background:none; border:none; cursor:pointer; }}

    .card {{ width:90%; max-width:360px; height:260px; perspective:1000px; margin:18px auto; }}
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
    .btn-small {{ padding:8px 12px; font-size:1em; background:#2d6cdf; color:#fff; border:none; border-radius:8px; cursor:pointer; }}
    .btn-green {{ background:#28a745; }}

    .result {{ margin-top:8px; font-size:.95em; min-height:1.2em; }}

    .nav-buttons {{ display:flex; gap:12px; margin-top:16px; }}
    .nav-button {{ padding:8px 12px; font-size:1em; background:#007bff; color:#fff; border:none; border-radius:8px; min-width:110px; cursor:pointer; }}
    .nav-button:disabled {{ background:#aaa; cursor:default; }}
  </style>
</head>
<body>
  <h1>{set_name} • Learn <button class="home-btn" onclick="goHome()">🏠</button></h1>

  <div class="card" id="cardContainer" aria-live="polite">
    <div class="card-inner" id="cardInner">
      <div class="side front" id="frontSide">
        <div class="cue" id="frontCue"></div>
        <div class="actions">
          <button class="btn-small" id="btnSayFront">Say it in Polish</button>
        </div>
        <div class="result" id="frontResult"></div>
      </div>
      <div class="side back" id="backSide">
        <div class="answer-phrase" id="answerPhrase"></div>
        <div class="answer-pron" id="answerPron"></div>
        <div class="actions">
          <button class="btn-small btn-green" id="btnPlay">Play</button>
        </div>
        <div class="result" id="backResult"></div>
      </div>
    </div>
  </div>

  <div class="nav-buttons">
    <button id="prevBtn" class="nav-button">Previous</button>
    <button id="nextBtn" class="nav-button">Next</button>
  </div>

  <!-- Azure Speech SDK -->
  <script src="https://aka.ms/csspeech/jsbrowserpackageraw"></script>

  <!-- Correct relative paths from /flashcards/{set}/index.html -->
  <script src="../../static/js/api.js"></script>
  <script src="../../static/js/session_state.js"></script>

  <script>
    // --- Data & state ---
    const cards = {cards_json};
    const setName = "{set_name}";
    const mode = "flashcards";
    let currentIndex = 0;

    // Scoring + points
    // - Score% is based on PASS (>=75)
    // - Points: 10 base for finishing + 1 per “100% before first flip” + 2x bonus if score==100
    const PASS = 75;
    const tracker = {{
      attempts: 0,
      per: {{}},               // per[idx] = {{ tries, best, got100BeforeFlip: boolean }}
      perfectNoFlipCount: 0,   // increments when avg==100 before first flip on that card
    }};
    let hasFlippedCurrent = false;

    // Mirror of Python sanitize_filename (for audio file names)
    function sanitizeFilename(text) {{
      return (text || "")
        .normalize("NFD")
        .replace(/[\\u0300-\\u036f]/g, "")
        .replace(/[^a-zA-Z0-9_-]+/g, "_")
        .replace(/^_+|_+$/g, "");
    }}

    function audioPath(index) {{
      const e = cards[index] || {{}};
      const fn = String(index) + "_" + sanitizeFilename(e.phrase || "") + ".mp3";
      return "../../static/" + encodeURIComponent(setName) + "/audio/" + encodeURIComponent(fn);
    }}

    function setNavUI() {{
      document.getElementById("prevBtn").disabled = (currentIndex === 0);
      const nextBtn = document.getElementById("nextBtn");
      nextBtn.textContent = (currentIndex < cards.length - 1) ? "Next" : "Finish";
    }}

    function renderCard() {{
      const e = cards[currentIndex] || {{}};
      // Front
      document.getElementById("frontCue").textContent = e.meaning || "";
      document.getElementById("frontResult").textContent = "";
      // Back
      document.getElementById("answerPhrase").textContent = e.phrase || "";
      document.getElementById("answerPron").textContent   = e.pronunciation || "";
      document.getElementById("backResult").textContent   = "";
      setNavUI();
      hasFlippedCurrent = false;  // reset flip flag each card
    }}

    async function assess(referenceText, targetEl) {{
      if (!referenceText) {{ targetEl.textContent = "—"; return; }}
      targetEl.textContent = "⏳ Listening…";

      if (!window.SpeechSDK) {{ targetEl.textContent = "❌ Azure SDK not loaded."; return; }}
      try {{
        const r = await api.fetch("/api/token");
        if (!r.ok) throw new Error("token");
        const data = await r.json();

        const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(data.token, data.region);
        speechConfig.speechRecognitionLanguage = "pl-PL";
        speechConfig.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "6000");
        speechConfig.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "1200");
        const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
        const recognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);

        const pa = new SpeechSDK.PronunciationAssessmentConfig(
          referenceText,
          SpeechSDK.PronunciationAssessmentGradingSystem.HundredMark,
          SpeechSDK.PronunciationAssessmentGranularity.Word,
          true
        );
        pa.applyTo(recognizer);

        recognizer.recognizeOnceAsync(result => {{
          try {{
            const resJson = result && result.json ? JSON.parse(result.json) : null;
            const words = resJson?.NBest?.[0]?.Words || [];
            const avg = words.length ? (words.reduce((a,b)=>a+(b.PronunciationAssessment?.AccuracyScore||0),0)/words.length).toFixed(1) : "0";

            // update tracker
            const rec = (tracker.per[currentIndex] = tracker.per[currentIndex] || {{ tries: 0, best: 0, got100BeforeFlip: false }});
            rec.tries += 1;
            tracker.attempts += 1;

            const numericAvg = Number(avg) || 0;
            rec.best = Math.max(rec.best, numericAvg);

            if (!hasFlippedCurrent && numericAvg === 100 && !rec.got100BeforeFlip) {{
              rec.got100BeforeFlip = true;
              tracker.perfectNoFlipCount += 1;
            }}

            // persist progress with per-card results
            if (window.SessionSync) SessionSync.save({{ setName, mode, progress: {{ index: currentIndex, per: tracker.per }} }});

            const ok = numericAvg >= PASS;
            const wordHtml = words.map(w => {{
              const score = w.PronunciationAssessment?.AccuracyScore || 0;
              const color = score >= 85 ? "green" : score >= 70 ? "orange" : "red";
              return `<span style="color:${{color}}; margin:0 4px;">${{w.Word}}</span>`;
            }}).join(" ");

            targetEl.innerHTML = `<div><strong>${{ok ? "Nice!" : "Not quite"}}:</strong> ${{avg}}%</div>` +
                                 (wordHtml ? `<div style="margin-top:5px;">${{wordHtml}}</div>` : "");
            if (!ok) targetEl.innerHTML += `<div style="margin-top:6px;">Flip the card to check the answer.</div>`;
          }} catch (err) {{
            console.warn("Parse error:", err);
            targetEl.textContent = "⚠️ Error parsing result.";
          }}
          recognizer.close();
        }}, err => {{
          console.error("Azure error:", err);
          targetEl.textContent = "❌ Recognition failed.";
          recognizer.close();
        }});
      }} catch (err) {{
        console.error("Azure token error:", err);
        targetEl.textContent = "❌ Azure token error.";
      }}
    }}

    // Wiring
    document.addEventListener("DOMContentLoaded", () => {{
      renderCard();

      // Flip on tap (ignore buttons/result)
      document.getElementById("cardContainer").addEventListener("click", (e) => {{
        if (e.target.closest("button") || e.target.classList.contains("result")) return;
        document.getElementById("cardContainer").classList.toggle("flipped");
        hasFlippedCurrent = true;
      }});

      // Front: Say it
      document.getElementById("btnSayFront").addEventListener("click", (e) => {{
        e.stopPropagation();
        const eCard = cards[currentIndex] || {{}};
        assess(eCard.phrase || "", document.getElementById("frontResult"));
      }});

      // Back: Play
      document.getElementById("btnPlay").addEventListener("click", (e) => {{
        e.stopPropagation();
        const audio = new Audio(audioPath(currentIndex));
        audio.play().catch(()=>{{}});
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
          // FINISH
          const totalCards = Math.max(1, cards.length);
          const correct = Object.values(tracker.per).filter(r => (r?.best || 0) >= PASS).length;
          const scorePct = Math.round((correct / totalCards) * 100);

          // Points:
          //  - base 10 for finishing
          //  - +1 per 100%-before-first-flip
          //  - if score==100, 2x the total
          let pointsTotal = 10 + tracker.perfectNoFlipCount;
          if (scorePct === 100) pointsTotal = pointsTotal * 2;

          // Cache locally for summary
          try {{
            localStorage.setItem("lp_last_result_" + setName, JSON.stringify({{
              score: scorePct,
              attempts: tracker.attempts,
              total: totalCards,
              points_total: pointsTotal,
              perfect_before_flip: tracker.perfectNoFlipCount
            }}));
          }} catch (_) {{}}

          // Submit to server
          let awarded = null;
          try {{
            const resp = await api.fetch("/api/submit_score", {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify({{
                set_name: setName,
                mode: "flashcards",
                score: scorePct,
                attempts: tracker.attempts,
                details: {{
                  per: tracker.per,
                  total: totalCards,
                  perfect_before_flip: tracker.perfectNoFlipCount,
                  points_total: pointsTotal
                }}
              }})
            }});
            if (resp.ok) {{
              const js = await resp.json();
              awarded = (js && js.details && js.details.points_awarded != null)
                ? Number(js.details.points_awarded) : null;
            }}
          }} catch (_) {{}}

          // Clear session state & go to summary
          try {{ if (window.SessionSync) await SessionSync.complete({{ setName, mode }}); }} catch(_){{
          }}
          try {{ localStorage.removeItem('lp_last'); }} catch(_){{}}
          const q = awarded != null ? ("?awarded=" + encodeURIComponent(awarded)) : "";
          window.location.href = "summary.html" + q;
        }}
      }});
    }});

    // Resume mid-set if ?resume=1
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
      // Always record "last activity" (Home "Continue" fallback)
      try {{ localStorage.setItem("lp_last", JSON.stringify({{ set_name:setName, mode, ts: Date.now() }})); }} catch(_){{
      }}
    }})();

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
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
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
      // pick up awarded delta from the redirect (?awarded=)
      const urlAwarded = (() => {{
        const v = new URL(location.href).searchParams.get('awarded');
        return (v != null) ? Number(v) : null;
      }})();

      let done = false, awarded = urlAwarded;

      // Server last score first
      try {{
        const r = await api.fetch('/api/get_scores?set_name=' + encodeURIComponent(setName) + '&limit=1');
        if (r.ok) {{
          const arr = await r.json();
          const last = Array.isArray(arr.scores) ? arr.scores[0] : null;
          if (last && last.set_name === setName) {{
            const d = last.details || {{}};
            if (awarded == null && d.points_awarded != null) awarded = Number(d.points_awarded);
            apply(Math.round(Number(last.score)||0), Number(last.attempts)||0, Number(d.total)||undefined,
                  Number(d.points_total)||undefined, awarded);
            done = true;
          }}
        }}
      }} catch (_) {{}}

      if (!done) {{
        // Fallback to local cache saved before redirect
        try {{
          const raw = localStorage.getItem('lp_last_result_' + setName);
          if (raw) {{
            const j = JSON.parse(raw);
            apply(Math.round(Number(j.score)||0), Number(j.attempts)||0, Number(j.total)||undefined,
                  Number(j.points_total)||undefined, awarded);
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
