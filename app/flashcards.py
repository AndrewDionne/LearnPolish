# app/flashcards.py
import json
from pathlib import Path

from .sets_utils import sanitize_filename

DOCS_DIR = Path("docs")


def generate_flashcard_html(set_name, data):
    """
    Generates docs/flashcards/<set_name>/index.html.

    ✅ Preserves functionality:
      - Flip card (meaning ⇄ phrase/pronunciation)
      - Prev/Next navigation
      - Azure pronunciation "Try" button (fetches /api/token)
      - Audio playback with the same filename convention: "<index>_<sanitized phrase>.mp3"
      - GitHub Pages vs local dev path handling for audio
    ❗ No dependency on per-set modes (set_modes.json) — fits new type-based system.
    """

    # Ensure output dir exists
    output_dir = DOCS_DIR / "flashcards" / set_name
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "index.html"

    # Keep audio filename convention consistent with existing pages/tools
    for idx, entry in enumerate(data):
        try:
            filename = f"{idx}_{sanitize_filename(entry.get('phrase', ''))}.mp3"
            entry["audio_file"] = filename  # not strictly required by the page, but preserved for compatibility
        except Exception:
            # If entry is malformed, still keep generating
            entry["audio_file"] = f"{idx}_.mp3"

    # Embed the set data (preserves current behavior)
    cards_json = json.dumps(data, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{set_name} Flashcards</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      margin: 0; padding: 20px;
      background-color: #f8f9fa;
      display: flex; flex-direction: column; align-items: center;
      justify-content: flex-start;
      min-height: 100vh;
      box-sizing: border-box;
      overflow-x: hidden;
    }}
    h1 {{
      font-size: 1.5em;
      margin-bottom: 20px;
      position: relative;
      width: 100%;
      text-align: center;
    }}
    .home-btn {{
      position: absolute;
      right: 0px;
      top: 0;
      font-size: 1.4em;
      background: none;
      border: none;
      cursor: pointer;
    }}
    .card {{
      width: 90%;
      max-width: 350px;
      height: 220px;
      perspective: 1000px;
      margin: 20px auto;
      box-sizing: border-box;
    }}
    .card-inner {{
      width: 100%;
      height: 100%;
      position: relative;
      transition: transform 0.6s;
      transform-style: preserve-3d;
      cursor: pointer;
      box-shadow: 0 4px 10px rgba(0,0,0,0.1);
      display: flex;
      justify-content: center;
      align-items: center;
      border-radius: 12px;
    }}
    .card.flipped .card-inner {{
      transform: rotateY(180deg);
    }}
    .card-front, .card-back {{
      position: absolute;
      width: 100%; height: 100%;
      border-radius: 12px;
      padding: 20px;
      backface-visibility: hidden;
      display: flex;
      justify-content: center;
      align-items: center;
      text-align: center;
      word-wrap: break-word;
    }}
    .card-front {{
      background: #ffffff;
      font-size: 1.1em;
    }}
    .card-back {{
      background: #e9ecef;
      transform: rotateY(180deg);
      flex-direction: column;
      font-size: 1.1em;
    }}
    .card-back .actions {{
      margin-top: auto;
      margin-bottom: 10px;
      display: flex;
      gap: 8px;
    }}
    .card-back button {{
      padding: 8px 12px;
      font-size: 1em;
      background-color: #28a745;
      border: none;
      border-radius: 8px;
      color: white;
      cursor: pointer;
    }}
    .nav-buttons {{
      display: flex;
      gap: 15px;
      margin-top: 20px;
    }}
    .nav-button {{
      padding: 6px 12px;
      font-size: 1em;
      background-color: #007bff;
      color: white;
      border: none;
      border-radius: 8px;
      width: 100px;
      height: 30px;
      cursor: pointer;
    }}
    .nav-button:disabled {{
      background-color: #aaa;
      cursor: default;
    }}
  </style>
</head>
<body>
 <h1>{set_name} Flashcards <button class="home-btn" onclick="goHome()">🏠</button></h1>

  <div class="card" id="cardContainer">
    <div class="card-inner" id="cardInner">
      <div class="card-front" id="cardFront"></div>
      <div class="card-back" id="cardBack"></div>
    </div>
  </div>

  <div class="nav-buttons">
    <button id="prevBtn" class="nav-button">Previous</button>
    <button id="nextBtn" class="nav-button">Next</button>
  </div>

  <audio id="audioPlayer">
    <source id="audioSource" src="" type="audio/mpeg" />
  </audio>

  <!-- Azure Speech SDK -->
  <script src="https://aka.ms/csspeech/jsbrowserpackageraw"></script>
  
  <script>
    // JS-side filename sanitizer (mirror of Python sanitize_filename)
    function sanitizeFilename(text) {{
      return (text || "")
        .normalize("NFD")
        .replace(/[\\u0300-\\u036f]/g, "")   // remove diacritics
        .replace(/[^a-zA-Z0-9_-]+/g, "_")    // non-alphanumeric → _
        .replace(/^_+|_+$/g, "");            // trim underscores
    }}

    const cards = {cards_json};
    const setName = "{set_name}";
    let currentIndex = 0;

    function updateCard() {{
      if (!cards.length) {{
        document.getElementById("cardFront").textContent = "No cards.";
        return;
      }}
      const entry = cards[currentIndex] || {{}};
      document.getElementById("cardFront").textContent = entry.meaning || "";
      document.getElementById("cardBack").innerHTML = `
        <div style="margin-bottom:6px;">${{entry.phrase || ""}}</div>
        <div><em>${{entry.pronunciation || ""}}</em></div>
        <div class="actions">
          <button onclick="playAudio('${{currentIndex}}_' + sanitizeFilename('${{entry.phrase || ""}}') + '.mp3')">▶️ Play</button>
          <button onclick="assessPronunciation('${{(entry.phrase || "").replace(/'/g, "\\'")}}')">🎤 Try</button>
        </div>
        <div id="pronunciationResult" style="margin-top:6px; font-size:0.9em;"></div>
      `;
      document.getElementById("prevBtn").disabled = currentIndex === 0;
      document.getElementById("nextBtn").disabled = currentIndex === cards.length - 1;
    }}

    document.addEventListener("DOMContentLoaded", () => {{
      if (!window.SpeechSDK) {{
        console.warn("Azure Speech SDK not loaded (network?).");
      }}
      updateCard();
    }});

    function repoBase() {{
      // For GitHub Pages: /<repo>/..., for local dev: /
      if (window.location.hostname === "andrewdionne.github.io") {{
        const parts = window.location.pathname.split("/").filter(Boolean);
        const repo = parts.length ? parts[0] : "LearnPolish";
        return "/" + repo;
      }}
      return "";
    }}

    function getAudioPath(filename) {{
      // GH Pages: /<repo>/static/<setName>/audio/<file>
      // Local dev: /custom_static/<setName>/audio/<file> (your dev server should serve this)
      if (window.location.hostname === "andrewdionne.github.io") {{
        return repoBase() + `/static/${{setName}}/audio/${{filename}}`;
      }} else {{
        return `/custom_static/${{setName}}/audio/${{filename}}`;
      }}
    }}

    function playAudio(filename, callback = () => {{}}) {{
      const audio = new Audio(getAudioPath(filename));
      audio.currentTime = 0;
      audio.onended = callback;
      audio.onerror = () => {{ console.warn("Audio failed:", filename); callback(); }};
      const playPromise = audio.play();
      if (playPromise !== undefined) {{
        playPromise.catch(err => {{
          console.warn("Autoplay blocked or error:", err);
          callback();
        }});
      }}
    }}

    async function assessPronunciation(referenceText) {{
      const resultDiv = document.getElementById("pronunciationResult");
      resultDiv.textContent = "⏳ Preparing microphone…";

      if (!window.SpeechSDK) {{
        resultDiv.textContent = "❌ Azure SDK not loaded.";
        return;
      }}

      const baseUrl = (window.location.hostname === "andrewdionne.github.io") ? "https://flashcards-5c95.onrender.com" : "";

      try {{
        // Fetch short-lived Azure token from your API
        const res = await fetch(`${{baseUrl}}/api/token`);
        const data = await res.json();

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

        setTimeout(() => {{
          resultDiv.innerHTML = `🎤 Say: <strong>${{referenceText}}</strong>`;
        }}, 1200);

        recognizer.recognizeOnceAsync(result => {{
          try {{
            const resJson = result && result.json ? JSON.parse(result.json) : null;
            const words = resJson && resJson.NBest && resJson.NBest[0].Words ? resJson.NBest[0].Words : [];
            const avg = words.length ? (words.reduce((a,b) => a + (b.PronunciationAssessment?.AccuracyScore || 0), 0) / words.length).toFixed(1) : "0";

            const wordHtml = words.map(w => {{
              const score = w.PronunciationAssessment?.AccuracyScore || 0;
              const color = score >= 85 ? "green" : score >= 70 ? "orange" : "red";
              return `<span style="color:${{color}}; margin:0 4px;">${{w.Word}}</span>`;
            }}).join(" ");

            resultDiv.innerHTML = `<div><strong>Overall:</strong> ${{avg}}%</div><div style="margin-top:5px;">${{wordHtml}}</div>`;
          }} catch (err) {{
            console.warn("Parse error:", err);
            resultDiv.textContent = "⚠️ Error parsing result.";
          }}
          recognizer.close();
        }}, err => {{
          console.error("Azure error:", err);
          resultDiv.textContent = "❌ Recognition failed.";
          recognizer.close();
        }});
      }} catch (err) {{
        console.error("Azure token error:", err);
        resultDiv.textContent = "❌ Azure token error.";
      }}
    }}

    document.getElementById("cardContainer").addEventListener("click", (e) => {{
      if (e.target.closest("button") || e.target.id === "pronunciationResult") return;
      document.getElementById("cardContainer").classList.toggle("flipped");
    }});
    document.getElementById("prevBtn").onclick = () => {{ if (currentIndex > 0) {{ currentIndex--; updateCard(); }} }};
    document.getElementById("nextBtn").onclick = () => {{ if (currentIndex < cards.length - 1) {{ currentIndex++; updateCard(); }} }};

    function goHome() {{
      if (window.location.hostname === "andrewdionne.github.io") {{
        window.location.href = repoBase() + "/";
      }} else {{
        window.location.href = "/";
      }}
    }}
  </script>
</body>
</html>
"""

    out_path.write_text(html, encoding="utf-8")
    print(f"✅ flashcards page generated: {out_path}")
    return out_path
