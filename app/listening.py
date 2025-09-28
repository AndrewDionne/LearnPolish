# app/listening.py
from pathlib import Path
import json
import random

# Keep parity with other modes (not used for paths; we allow spaces)
try:
    from .sets_utils import sanitize_filename  # noqa: F401
except Exception:  # pragma: no cover
    def sanitize_filename(name: str) -> str:
        return "".join(c for c in name if c.isalnum() or c in (" ", "-", "_", ".")).rstrip()

DOCS_DIR = Path("docs")


def _load_listening_data(set_name: str):
    """Load dialogues.json for a listening set. Returns list of dialogues.

    Expected folder structure:
    docs/listening/<set_name>/
      - meta.json (optional, not required here)
      - dialogues.json (required)
      - audio/ (mp3 files referenced by dialogues.json)
    """
    d = DOCS_DIR / "listening" / set_name
    data_path = d / "dialogues.json"
    if not data_path.exists():
        raise FileNotFoundError(f"Missing {data_path}. Create it with your dialogue items.")
    with data_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("dialogues.json must be a JSON array of dialogue objects.")
    return data


def generate_listening_html(set_name: str, data=None):
    """
    Generate Listening Mode page:
      - docs/listening/<set_name>/index.html

    Behavior:
      • No text before questions; audio-first.
      • Controls: Play/Pause, 0.75× toggle (one-time cost per dialogue), Replay (max 3, each costs gold).
      • After audio ends → Gist MCQ (4 options) → Detail MCQ (4 options sampled from a 10-item bank).
      • Then reveal Polish transcript + English translation.
      • Gold economy (defaults; tweakable in the JSON config at the top of the page script):
          - Session bonus: +20 once per visit (tracked in page state)
          - Base per-dialogue: 10 gold
          - Length bonus: +1 per 20s of audio (cap +5)
          - Costs: slow toggle −2 (once), each replay −1, each wrong attempt −1 (up to 3 tries per Q)
          - Weighting: 40% gist / 60% detail; penalties for wrong gist hit gist share, detail hit detail share
          - Floor 0 per dialogue
    """
    out_dir = DOCS_DIR / "listening" / set_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.html"

    # Load data automatically if not provided
    if data is None:
        data = _load_listening_data(set_name)

    # Inject data as JSON for client-side (escape </script>)
    dialogues_json = json.dumps(data, ensure_ascii=False)
    dialogues_json_safe = dialogues_json.replace("</", "<\\/")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{set_name} • Listening Mode</title>
  <style>
    :root{{
      --bg:#0b0c10; --card:#121418; --text:#e9ecf1; --muted:#8b94a7; --accent:#2d6cdf; --good:#2dcf6c; --bad:#ff5a5f;
      --pad:16px; --radius:14px; --shadow:0 8px 24px rgba(0,0,0,.25);
    }}
    @media (prefers-color-scheme: light){{
      :root{{ --bg:#f7f7fb; --card:#ffffff; --text:#0c0f14; --muted:#5a6472; --shadow:0 8px 24px rgba(0,0,0,.08); }}
    }}
    html,body{{margin:0;padding:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Inter,system-ui,sans-serif;}}
    header{{position:sticky;top:0;background:var(--bg);padding:12px var(--pad);display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(128,128,128,.15);z-index:10;}}
    .title{{font-weight:700;}}
    .pill{{font-size:.9rem;color:var(--muted);}}
    .wrap{{max-width:900px;margin:0 auto;padding:var(--pad);}}
    .card{{background:var(--card);border-radius:var(--radius);box-shadow:var(--shadow);padding:20px;margin:16px 0;}}
    .player{{display:flex;gap:12px;align-items:center;}}
    button{{appearance:none;border:0;background:var(--accent);color:white;border-radius:12px;padding:10px 14px;font-weight:600;cursor:pointer;}}
    button.ghost{{background:transparent;color:var(--text);border:1px solid rgba(128,128,128,.3);}}
    button[disabled]{{opacity:.5;cursor:not-allowed;}}
    .choices{{display:grid;grid-template-columns:1fr;gap:10px;margin-top:10px;}}
    .choice{{background:#1a1f27;border:1px solid rgba(128,128,128,.25);padding:12px;border-radius:12px;}}
    @media (prefers-color-scheme: light){{ .choice{{background:#fff;}} }}
    .choice.correct{{outline:2px solid var(--good);}}
    .choice.wrong{{outline:2px solid var(--bad);}}
    .meta{{display:flex;gap:12px;align-items:center;color:var(--muted);font-size:.95rem;}}
    .section-title{{font-weight:700;margin:0 0 6px;}}
    .row{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;}}
    .grow{{flex:1;}}
    .hidden{{display:none;}}
    .tr{{white-space:pre-wrap;color:var(--muted);}}
    .footer{{display:flex;justify-content:space-between;align-items:center;margin-top:8px;}}
    .tag{{background:rgba(128,128,128,.15);color:var(--text);border-radius:999px;padding:6px 10px;font-size:.85rem;}}
  </style>
</head>
<body>
  <header class="wrap">
    <div class="title">🎧 Listening • {set_name}</div>
    <div class="pill"><span id="gold">0</span> gold • <span id="progress">0/0</span></div>
  </header>

  <main class="wrap">
    <div class="card">
      <div class="row" style="justify-content:space-between;">
        <div class="meta"><span id="countLabel"></span><span id="lengthLabel"></span><span id="replayLabel"></span></div>
        <div class="row"><button class="ghost" id="homeBtn">🏠 Home</button></div>
      </div>
      <div class="player" style="margin-top:8px;">
        <button id="playBtn">▶️ Play</button>
        <button class="ghost" id="speedBtn">0.75×</button>
        <button class="ghost" id="replayBtn">Replay (3)</button>
        <audio id="audio" preload="auto"></audio>
      </div>
    </div>

    <div class="card" id="gistCard" aria-live="polite">
      <div class="section-title">Gist</div>
      <div id="gistPrompt"></div>
      <div class="choices" id="gistChoices"></div>
    </div>

    <div class="card" id="detailCard" aria-live="polite">
      <div class="section-title">Details</div>
      <div id="detailPrompt"></div>
      <div class="choices" id="detailChoices"></div>
    </div>

    <div class="card" id="revealCard">
      <div class="section-title">Transcript</div>
      <div class="tr" id="plText"></div>
      <div style="height:6px"></div>
      <div class="section-title">English</div>
      <div class="tr" id="enText"></div>
    </div>

    <div class="footer">
      <div class="row" style="gap:6px;">
        <span class="tag">Rate difficulty:</span>
        <button class="ghost" id="rEasy">Too easy</button>
        <button class="ghost" id="rOk">Just right</button>
        <button class="ghost" id="rHard">Too hard</button>
      </div>
      <div class="row">
        <button id="nextBtn" disabled>Next ▶</button>
      </div>
    </div>

    <div class="card" id="summaryCard">
      <div class="section-title">Session Summary</div>
      <div id="summaryBody"></div>
      <div class="row" style="margin-top:10px;">
        <button id="restartBtn" class="ghost">Restart</button>
        <button id="toHomeBtn">Done</button>
      </div>
    </div>
  </main>

  <script>
  // ————— Config (tweak without touching Python) —————
  const CONFIG = {{
    sessionBonus: 20,
    basePerDialogue: 10,
    lengthBonusEverySec: 20, // +1 per 20s
    lengthBonusCap: 5,
    slowCost: 2,
    replayCost: 1,
    wrongCost: 1,
    replayMax: 3,
    weightGist: 0.4,
    weightDetail: 0.6,
    triesPerQuestion: 3,
  }};

  const SET_NAME = {json.dumps(set_name)};
  const DIALOGUES = {dialogues_json_safe};


  // ————— State —————
  const state = {{
    i: 0,
    gold: 0,
    usedSlow: false,
    replays: 0,
    wrongGist: 0,
    wrongDetail: 0,
    answeredGist: false,
    answeredDetail: false,
    gistTriesLeft: CONFIG.triesPerQuestion,
    detailTriesLeft: CONFIG.triesPerQuestion,
    currentDurationS: 0,
    perDialogueLog: [],
    started: false,
  }};

  // ————— DOM helpers —————
  const $ = (id) => document.getElementById(id);
  const playBtn = $("playBtn");
  const speedBtn = $("speedBtn");
  const replayBtn = $("replayBtn");
  const nextBtn = $("nextBtn");
  const homeBtn = $("homeBtn");
  const toHomeBtn = $("toHomeBtn");
  const restartBtn = $("restartBtn");
  const audioEl = $("audio");

  const gistCard = $("gistCard");
  const gistPrompt = $("gistPrompt");
  const gistChoices = $("gistChoices");

  const detailCard = $("detailCard");
  const detailPrompt = $("detailPrompt");
  const detailChoices = $("detailChoices");

  const revealCard = $("revealCard");
  const plText = $("plText");
  const enText = $("enText");

  const summaryCard = $("summaryCard");
  const summaryBody = $("summaryBody");

  const goldLbl = $("gold");
  const progressLbl = $("progress");
  const countLabel = $("countLabel");
  const lengthLabel = $("lengthLabel");
  const replayLabel = $("replayLabel");

  function repoBase() {{
    // Matches patterns used in other modes hosted on GitHub Pages
    const p = window.location.pathname.split("/").filter(Boolean);
    if (window.location.hostname.includes("github.io")) {{
      // /<repo>/listening/<set>/
      return "/" + p[0];
    }}
    return "";
  }}

  function gotoHome() {{
    if (window.location.hostname.includes("github.io")) {{
      window.location.href = repoBase() + "/";
    }} else {{
      window.location.href = "/";
    }}
  }}

  // ————— Utils —————
  function shuffle(arr) {{
    for (let i = arr.length - 1; i > 0; i--) {{
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }}
    return arr;
  }}
  function sampleDetailChoices(item) {{
    const bank = (item.detail?.distractor_bank || []).slice();
    const correct = item.detail?.correct ?? "";
    const pruned = bank.filter(x => x !== correct);
    shuffle(pruned);
    const three = pruned.slice(0, 3);
    const combined = [correct, ...three];
    return shuffle(combined);
  }}

  function computePool(item, usedSlow, replays, wrongGist, wrongDetail) {{
    const base = CONFIG.basePerDialogue;
    const dur = (item.duration_s || state.currentDurationS || 0);
    const lenBonus = Math.min(CONFIG.lengthBonusCap, Math.floor(dur / CONFIG.lengthBonusEverySec));
    let pool = base + lenBonus;
    // Global penalties
    pool -= (usedSlow ? CONFIG.slowCost : 0);
    pool -= (replays * CONFIG.replayCost);
    if (pool < 0) pool = 0;
    // Shares
    const gShare = pool * CONFIG.weightGist;
    const dShare = pool * CONFIG.weightDetail;
    const gEarn = Math.max(0, Math.floor(gShare - wrongGist * CONFIG.wrongCost));
    const dEarn = Math.max(0, Math.floor(dShare - wrongDetail * CONFIG.wrongCost));
    return Math.max(0, gEarn + dEarn);
  }}

  function setHidden(el, hidden=true) {{ el.classList.toggle("hidden", hidden); }}
  function resetQuestionUI() {{
    gistChoices.innerHTML = ""; detailChoices.innerHTML = "";
    [gistCard, detailCard, revealCard, summaryCard].forEach(el => setHidden(el, true));
    nextBtn.disabled = true;
  }}

  function setHeader() {{
    goldLbl.textContent = state.gold;
    progressLbl.textContent = `${{state.i+1}}/${{DIALOGUES.length}}`;
    countLabel.textContent = `Dialog ${{state.i+1}} of ${{DIALOGUES.length}}`;
    const dur = (DIALOGUES[state.i]?.duration_s || state.currentDurationS || 0);
    lengthLabel.textContent = dur ? `• ${{dur}}s` : "";
    replayLabel.textContent = `• Replays left: ${{CONFIG.replayMax - state.replays}}`;
  }}

  function beginSessionIfNeeded() {{
    if (!state.started) {{
      state.gold += CONFIG.sessionBonus;
      state.started = true;
      goldLbl.textContent = state.gold;
    }}
  }}

  function audioUrlFor(item){{
    // Prefer absolute URL if provided
    if (item.audio_url) return item.audio_url;

    const rel = (item.audio || "").replace(/^\/+/, "");
    if (!rel) return "";

    const encSet = encodeURIComponent(SET_NAME);
    if (window.location.hostname.includes("github.io")){{
      // GitHub Pages: serve from /static/<set>/<rel>
      return repoBase() + `/static/${{encSet}}/${{rel}}`;
    }}
    // Local dev: served by /custom_static → docs/static
    return `/custom_static/${{encSet}}/${{rel}}`;
  }}

  function loadAudio(item) {{
    const src = audioUrlFor(item);
    if (!src) {{
      console.warn("No audio for item", item);
      audioEl.removeAttribute("src");
      return;
    }}
    audioEl.src = src;
    audioEl.playbackRate = state.usedSlow ? 0.75 : 1.0;
  }}


  function renderGist(item) {{
    if (!item.gist) return;
    setHidden(gistCard, false);
    gistPrompt.textContent = item.gist.prompt || "What is the gist?";
    const opts = shuffle([ item.gist.correct, ...(item.gist.distractors || []).slice(0,3) ]);
    gistChoices.innerHTML = "";
    opts.forEach((txt) => {{
      const b = document.createElement("button");
      b.className = "choice"; b.textContent = txt;
      b.onclick = () => onGistAnswer(item, b, txt === item.gist.correct);
      gistChoices.appendChild(b);
    }});
  }}

  function renderDetail(item) {{
    if (!item.detail) return;
    setHidden(detailCard, false);
    detailPrompt.textContent = item.detail.prompt || "What detail did you hear?";
    const opts = sampleDetailChoices(item);
    detailChoices.innerHTML = "";
    opts.forEach((txt) => {{
      const b = document.createElement("button");
      b.className = "choice"; b.textContent = txt;
      b.onclick = () => onDetailAnswer(item, b, txt === item.detail.correct);
      detailChoices.appendChild(b);
    }});
  }}

  function renderReveal(item) {{
    plText.textContent = item.transcript_pl || "(no transcript)";
    enText.textContent = item.translation_en || "";
    setHidden(revealCard, false);
  }}

  function lockChoices(containerId) {{
    const children = document.getElementById(containerId).children;
    for (const c of children) c.disabled = true;
  }}

  function onGistAnswer(item, btn, correct) {{
    if (state.answeredGist) return;
    if (correct) {{
      btn.classList.add("correct");
      state.answeredGist = true;
      lockChoices("gistChoices");
      if (!state.answeredDetail) renderDetail(item);
      if (state.answeredDetail) finalizeDialogue(item);
      return;
    }}
    // wrong
    btn.classList.add("wrong");
    btn.disabled = true;
    state.wrongGist++;
    state.gistTriesLeft--;
    if (state.gistTriesLeft <= 0) {{
      state.answeredGist = true;
      // show correct
      [...gistChoices.children].forEach(c => {{
        if (c.textContent === (item.gist?.correct || "")) c.classList.add("correct");
        c.disabled = true;
      }});
      if (!state.answeredDetail) renderDetail(item);
      if (state.answeredDetail) finalizeDialogue(item);
    }}
  }}

  function onDetailAnswer(item, btn, correct) {{
    if (state.answeredDetail) return;
    if (correct) {{
      btn.classList.add("correct");
      state.answeredDetail = true;
      lockChoices("detailChoices");
      if (state.answeredGist) finalizeDialogue(item);
      return;
    }}
    // wrong
    btn.classList.add("wrong");
    btn.disabled = true;
    state.wrongDetail++;
    state.detailTriesLeft--;
    if (state.detailTriesLeft <= 0) {{
      state.answeredDetail = true;
      // show correct
      [...detailChoices.children].forEach(c => {{
        if (c.textContent === (item.detail?.correct || "")) c.classList.add("correct");
        c.disabled = true;
      }});
      if (state.answeredGist) finalizeDialogue(item);
    }}
  }}

  function finalizeDialogue(item) {{
    // Compute payout
    const gained = computePool(item, state.usedSlow, state.replays, state.wrongGist, state.wrongDetail);
    state.gold += gained;
    state.perDialogueLog.push({{
      id: item.id || `d${{state.i+1}}`,
      usedSlow: state.usedSlow,
      replays: state.replays,
      wrongGist: state.wrongGist,
      wrongDetail: state.wrongDetail,
      payout: gained,
      duration_s: item.duration_s || state.currentDurationS || 0,
    }});
    goldLbl.textContent = state.gold;
    renderReveal(item);
    nextBtn.disabled = false;
  }}

  function resetPerDialogue() {{
    state.usedSlow = false;
    state.replays = 0;
    state.wrongGist = 0;
    state.wrongDetail = 0;
    state.answeredGist = false;
    state.answeredDetail = false;
    state.gistTriesLeft = CONFIG.triesPerQuestion;
    state.detailTriesLeft = CONFIG.triesPerQuestion;
    state.currentDurationS = 0;
    replayBtn.textContent = `Replay (${{CONFIG.replayMax}})`;
    replayBtn.disabled = false;
    speedBtn.disabled = false;
  }}

  function startDialogue(idx) {{
    if (idx >= DIALOGUES.length) return endSession();
    resetPerDialogue(); resetQuestionUI();
    const item = DIALOGUES[idx];
    // prefer authored duration until metadata loads
    state.currentDurationS = Math.round(item?.duration_s || 0);
    setHeader();
    loadAudio(item);
  }}

  function endSession() {{
    setHidden(gistCard,true); setHidden(detailCard,true); setHidden(revealCard,true);
    setHidden(summaryCard,false);
    const rows = state.perDialogueLog.map((r, k) => `#${{k+1}} • +${{r.payout}} gold • replay:${{r.replays}} • slow:${{r.usedSlow?'y':'n'}} • gist×${{r.wrongGist}} • detail×${{r.wrongDetail}}`).join("\\n");
    summaryBody.textContent = `Total gold: ${{state.gold}}\\n\\n${{rows}}`;
  }}

  // ————— Wire up —————
  playBtn.onclick = () => {{
    beginSessionIfNeeded();
    audioEl.play().catch(()=>{{}});
  }};
  speedBtn.onclick = () => {{
    if (state.usedSlow) return; // single-cost per dialogue
    state.usedSlow = true; audioEl.playbackRate = 0.75; speedBtn.disabled = true; // gold cost accounted at finalize
  }};
  replayBtn.onclick = () => {{
    if (state.replays >= CONFIG.replayMax) return;
    state.replays++; replayBtn.textContent = `Replay (${{CONFIG.replayMax - state.replays}})`;
    setHeader();
    audioEl.currentTime = 0; audioEl.play().catch(()=>{{}});
    if (state.replays >= CONFIG.replayMax) replayBtn.disabled = true;
  }};
  nextBtn.onclick = () => {{ state.i++; if (state.i >= DIALOGUES.length) endSession(); else startDialogue(state.i); }};
  homeBtn.onclick = gotoHome; toHomeBtn.onclick = gotoHome; restartBtn.onclick = () => window.location.reload();

  $("rEasy").onclick = () => console.log("rated: easy", DIALOGUES[state.i]?.id);
  $("rOk").onclick   = () => console.log("rated: ok", DIALOGUES[state.i]?.id);
  $("rHard").onclick = () => console.log("rated: hard", DIALOGUES[state.i]?.id);

  audioEl.addEventListener('ended', () => {{
    // When audio finishes, show gist question
    const item = DIALOGUES[state.i];
    renderGist(item);
  }});

  audioEl.addEventListener('loadedmetadata', () => {{
    const d = isFinite(audioEl.duration) ? Math.round(audioEl.duration) : 0;
    if (d > 0) state.currentDurationS = d;
    setHeader();
  }});

  // Initial mount
  (function init() {{
    if (!Array.isArray(DIALOGUES) || DIALOGUES.length === 0) {{
      document.body.innerHTML = '<div style="padding:20px;font-family:sans-serif;">⚠️ No dialogues found for this set.</div>';
      return;
    }}
    setHidden(gistCard,true); setHidden(detailCard,true); setHidden(revealCard,true); setHidden(summaryCard,true);
    state.gold = 0;
    startDialogue(0);
  }})();
  </script>
</body>
</html>
"""

    out_path.write_text(html, encoding="utf-8")
    print(f"✅ listening page generated: {out_path}")
    return out_path


# === Creation helpers: turn simple `listen` arrays into `dialogues.json` and write files ===

def _is_dialogues_format(items):
    """Treat as authored dialogues only if MCQ fields exist; otherwise coerce."""
    try:
        first = items[0]
    except Exception:
        return False
    if not isinstance(first, dict):
        return False
    has_mcq = ("gist" in first) or ("detail" in first)
    return bool(has_mcq)


def _coerce_simple_listen_to_dialogues(items):
    """Convert a flat array like [{audio|audio_url, phrase?, meaning?}] into dialogues.json entries
    that Listening Mode can run (with gist/detail MCQs auto-built from peer items).
    """
    # Gather corpora for distractors
    phrases = [str(x.get("phrase") or x.get("polish") or "").strip() for x in items]
    meanings = [str(x.get("meaning") or x.get("english") or "").strip() for x in items]

    # Fallback distractors if the set is tiny
    fallback_meaning = [
        "A greeting", "An apology", "A request", "A question",
        "Directions", "Small talk", "A number", "A time of day",
    ]

    out = []
    for idx, it in enumerate(items, start=1):
        audio = it.get("audio") or it.get("audio_url") or ""
        pl = str(it.get("phrase") or it.get("polish") or "").strip()
        en = str(it.get("meaning") or it.get("english") or "").strip()

        # Build gist options: correct English meaning + 3 other meanings
        other_meanings = [m for m in meanings if m and m != en]
        random.shuffle(other_meanings)
        gist_distractors = other_meanings[:3]
        if len(gist_distractors) < 3:
            # top up with generic fallbacks not equal to `en`
            pool = [x for x in fallback_meaning if x != en]
            random.shuffle(pool)
            need = 3 - len(gist_distractors)
            gist_distractors += pool[:need]

        # Detail distractor bank: other Polish phrases (up to 10)
        other_phrases = [p for p in phrases if p and p != pl]
        random.shuffle(other_phrases)
        bank = other_phrases[:10]
        # If no Polish text given, mirror meanings to keep UI working
        if not pl:
            pl = en  # last resort so the MCQ isn't empty
        if not en:
            en = pl  # keep both sides non-empty

        out.append({
            "id": f"d{idx:03d}",
            "audio": audio,
            "duration_s": int(it.get("duration_s") or 0),
            "transcript_pl": pl,
            "translation_en": en,
            "gist": {
                "prompt": "Which best matches the audio?",
                "correct": en,
                "distractors": gist_distractors
            },
            "detail": {
                "prompt": "What exactly did you hear (in Polish)?",
                "correct": pl,
                "distractor_bank": bank
            }
        })
    return out


def save_listening_set(set_name: str, items):
    """Write meta.json + dialogues.json for a listening set. Accepts either full dialogues
    or simple-listen items and will coerce as needed. Returns output directory path.
    """
    base = DOCS_DIR / "listening" / set_name
    base.mkdir(parents=True, exist_ok=True)

    # Normalize to dialogues format
    dialogues = items if _is_dialogues_format(items) else _coerce_simple_listen_to_dialogues(items)

    # Minimal meta
    meta = {
        "set_name": set_name,
        "description": "Auto-generated listening set (can be edited).",
        "tags": ["listening"],
        "recommended_session_size": min(10, len(dialogues) or 10),
        "advanced_mode_available": False,
        "distractor_bank_policy": "Detail draws 3 from a bank each run."
    }

    # Write files (first pass; audio refs will be rewritten by prerender later)
    (base / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (base / "dialogues.json").write_text(json.dumps(dialogues, ensure_ascii=False, indent=2), encoding="utf-8")
    return base

def render_missing_audio_for_listening(set_name: str, voice_lang: str = "pl"):
    """
    For each dialogue in docs/listening/<set>/dialogues.json:
      - If 'audio_url' is present, leave as-is.
      - Else synthesize MP3 from transcript_pl (or detail.correct/translation_en fallback)
        into docs/static/<set>/listening/dXXX.mp3, and set item["audio"] = "listening/dXXX.mp3".
    Uses gTTS to match other modes' pipeline.
    """
    from gtts import gTTS  # lazy import to avoid hard dependency if unused

    # Read dialogues
    base = DOCS_DIR / "listening" / set_name
    dlg_path = base / "dialogues.json"
    if not dlg_path.exists():
        raise FileNotFoundError(f"Missing {dlg_path}")

    try:
        dialogues = json.loads(dlg_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid dialogues.json: {e}")

    # Output dir under docs/static (same convention as other modes)
    static_dir = DOCS_DIR / "static" / set_name / "listening"
    static_dir.mkdir(parents=True, exist_ok=True)

    changed = False
    for idx, item in enumerate(dialogues, start=1):
        # Skip if an absolute/remote URL is provided
        if item.get("audio_url"):
            continue

        # If we already have a local rel path ("listening/…") and file exists, keep it
        existing_rel = item.get("audio") or ""
        if existing_rel:
            candidate = DOCS_DIR / "static" / set_name / existing_rel
            if candidate.exists():
                continue  # already rendered & referenced

        # Pick text: prefer Polish transcript, then detail.correct, then English translation
        text = (
            (item.get("transcript_pl") or "").strip()
            or (item.get("detail", {}).get("correct") or "").strip()
            or (item.get("translation_en") or "").strip()
        )
        if not text:
            # Nothing to synthesize, just leave empty (UI will warn in console)
            continue

        # Render MP3
        filename = f"d{idx:03d}.mp3"
        out_path = static_dir / filename
        try:
            if not out_path.exists():
                tts = gTTS(text=text, lang=voice_lang)
                tts.save(str(out_path))
        except Exception as e:
            # Do not fail set creation because of one item; just continue
            print(f"[listen] gTTS failed for {set_name} #{idx}: {e}")
            continue

        # Rewrite item to point at the static-relative path (like other modes)
        item["audio"] = f"listening/{filename}"
        # If duration was not authored, keep or set 0; actual length will be picked up client-side
        changed = True

    if changed:
        dlg_path.write_text(json.dumps(dialogues, ensure_ascii=False, indent=2), encoding="utf-8")
    return changed


def create_listening_set(set_name: str, items):
    """Create listening set, render any missing audio to docs/static/<set>/listening/,
    rewrite dialogues.json to point at those files, then generate the HTML page.
    """
    out_dir = save_listening_set(set_name, items)

    # Render MP3s into docs/static/<set>/listening and rewrite 'audio' fields
    try:
        render_missing_audio_for_listening(set_name)
    except Exception as e:
        print(f"[listen] prerender skipped/failed for {set_name}: {e}")

    # Regenerate HTML using the (possibly updated) dialogues
    with (out_dir / "dialogues.json").open("r", encoding="utf-8") as f:
        dialogues = json.load(f)
    return generate_listening_html(set_name, dialogues)
