import os
import json
from pathlib import Path
from .sets_utils import load_set_modes, sanitize_filename

def generate_flashcard_html(set_name, data):
    """
    Generates flashcards.html for a set, with GitHub Pages–friendly paths and consistent audio/flip behavior.
    """

    # ✅ Mode-aware safeguard — only build if assigned to flashcards mode
    set_modes = load_set_modes()
    if "flashcards" in set_modes and set_name not in set_modes["flashcards"]:
        print(f"⏭️ Skipping flashcards for '{set_name}' (not in flashcards mode).")
        return None

    # ✅ Ensure output dir exists
    output_dir = Path("docs/output") / set_name
    output_dir.mkdir(parents=True, exist_ok=True)
    flashcard_path = output_dir / "flashcards.html"

    # ✅ Build audio paths (use /custom_static so Flask + GitHub Pages both work)
    for idx, entry in enumerate(data):
        filename = f"{idx}_{sanitize_filename(entry['phrase'])}.mp3"
        entry["audio_file"] = f"/custom_static/{set_name}/audio/{filename}"

    # Prepare JSON for embedding in HTML
    cards_json = json.dumps(data, ensure_ascii=False)

    # ✅ Full HTML with flip + audio fixes
    flashcard_html = f"""<!DOCTYPE html>
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
    .card-back button {{
      margin-top: auto;
      margin-bottom: 20px;
      padding: 8px 16px;
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

  <script src="https://aka.ms/csspeech/jsbrowserpackageraw"></script>
  <script>
    const cards = {cards_json};
    const setName = "{set_name}";
    let currentIndex = 0;

    function updateCard() {{
      const entry = cards[currentIndex];
      document.getElementById("cardFront").textContent = entry.meaning;
      document.getElementById("cardBack").innerHTML = `
        <p>${{entry.phrase}}</p>
        <p><em>${{entry.pronunciation}}</em></p>
        <button onclick="playAudio('${{entry.audio_file}}')">▶️ Play</button>
        <button onclick="assessPronunciation('${{entry.phrase}}')">🎤 Try</button>
        <div id="pronunciationResult" style="margin-top:10px; font-size:0.9em;"></div>
      `;
      document.getElementById("prevBtn").disabled = currentIndex === 0;
      document.getElementById("nextBtn").disabled = currentIndex === cards.length - 1;
    }}
    document.addEventListener("DOMContentLoaded", () => {{
        if (!window.SpeechSDK) {{
            console.error("❌ Azure Speech SDK failed to load.");
        }} else {{
            console.log("✅ Azure Speech SDK loaded successfully.");
        }}
    }});
    function playAudio(audioPath) {{
      const audio = document.getElementById("audioPlayer");
      const source = document.getElementById("audioSource");
      source.src = audioPath;   // ✅ direct use of path from Python
      audio.load();
      audio.play();
    }}

    function assessPronunciation(referenceText) {{
      const resultDiv = document.getElementById("pronunciationResult");
      if (!window.SpeechSDK) {{
        resultDiv.innerHTML = "❌ Azure SDK not loaded."; return;
      }}

      fetch("/api/token").then(r => r.json()).then(data => {{
        const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(data.token, data.region);
        speechConfig.speechRecognitionLanguage = "pl-PL";
        speechConfig.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "3000");
        speechConfig.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "1000");
        const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
        const recognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);
        const config = new SpeechSDK.PronunciationAssessmentConfig(referenceText, SpeechSDK.PronunciationAssessmentGradingSystem.HundredMark, SpeechSDK.PronunciationAssessmentGranularity.FullText, false);
        config.applyTo(recognizer);
        recognizer.recognized = (s, e) => {{
          try {{
            const res = JSON.parse(e.result.json);
            const score = res.NBest[0].PronunciationAssessment.AccuracyScore.toFixed(1);
            resultDiv.innerHTML = score >= 85 ? `🌟 ${{score}}%` : score >= 70 ? `✅ ${{score}}%` : `⚠️ ${{score}}%`;
          }} catch (err) {{
            resultDiv.innerHTML = "⚠️ Could not assess.";
          }}
          recognizer.stopContinuousRecognitionAsync();
        }};
        recognizer.startContinuousRecognitionAsync();
      }});
    }}

    document.getElementById("cardContainer").addEventListener("click", (e) => {{
      // Ignore clicks on buttons or result div
      if (e.target.closest("button") || e.target.id === "pronunciationResult") return;
      document.getElementById("cardContainer").classList.toggle("flipped");
    }});

    document.getElementById("prevBtn").onclick = () => {{ if (currentIndex > 0) {{ currentIndex--; updateCard(); }} }};
    document.getElementById("nextBtn").onclick = () => {{ if (currentIndex < cards.length - 1) {{ currentIndex++; updateCard(); }} }};

    function goHome() {{
      const pathParts = window.location.pathname.split("/");
      const repo = pathParts[1];
      window.location.href = window.location.hostname === "andrewdionne.github.io" ? `/${{repo}}/` : "/";
    }}

    updateCard();

  </script>
</body>
</html>
"""

    # Write to file
    with open(flashcard_path, "w", encoding="utf-8") as f:
        f.write(flashcard_html)

    print(f"✅ flashcards.html generated for: {set_name}")
    return flashcard_html