# app/listening.py
from __future__ import annotations

from pathlib import Path
import json
import os
import random
from html import escape as _esc

from .constants import PAGES_DIR, STATIC_DIR

# Optional R2 integration (safe if missing)
try:
    from app.r2_client import enabled as r2_enabled, put_file as r2_put_file
except Exception:  # pragma: no cover
    r2_enabled = False
    def r2_put_file(*_a, **_k):  # type: ignore
        return None

# Keep parity with other modes (not used for paths; we allow spaces)
try:
    from .sets_utils import sanitize_filename  # noqa: F401
except Exception:  # pragma: no cover
    def sanitize_filename(name: str) -> str:
        return "".join(c for c in name if c.isalnum() or c in (" ", "-", "_", ".")).rstrip()

# Prefer the shared Azure→gTTS helper from sets_utils; fall back to local gTTS if missing
try:
    from .sets_utils import _tts_to_mp3  # type: ignore
except Exception:  # pragma: no cover
    def _tts_to_mp3(text, out_path, voice=None):
        try:
            from gtts import gTTS
            out_path.parent.mkdir(parents=True, exist_ok=True)
            gTTS(text=str(text or ""), lang="pl").save(str(out_path))
            return True
        except Exception as e:
            print(f"[listen] local gTTS fallback failed: {e}")
            return False

# ---------------- Listening helpers ----------------

FALLBACK_DISTRACTORS = [
    "Small talk", "Directions", "An apology", "A question",
    "A reminder", "A warning", "A joke", "A greeting"
]

def _text(v):
    return (str(v).strip() if isinstance(v, (str, int, float)) else "").strip()

def _synth_distractors(correct, pool, n=3):
    correct = _text(correct)
    seen = {correct}
    out = []
    for cand in pool:
        t = _text(cand)
        if not t or t in seen:
            continue
        out.append(t)
        seen.add(t)
        if len(out) >= n:
            break
    if len(out) < n:
        for fb in FALLBACK_DISTRACTORS:
            if fb not in seen:
                out.append(fb)
                seen.add(fb)
                if len(out) >= n:
                    break
    return out[:n]

def normalize_listening_items(set_name: str, raw_items: list[dict]) -> list[dict]:
    """
    Accept mixed schemas and guarantee:
      - transcript_pl / translation_en are non-empty (use '—' as last resort)
      - gist/detail MCQs always have distractors
      - audio fields:
          * 'audio_url' (absolute URL) is honored as-is on the client
          * 'audio' is a set-relative static key (e.g., 'listening/d001.mp3'), resolved by the client
    """
    items = raw_items or []
    pool_en = []
    pool_pl = []
    for it in items:
        pool_en.append(_text(it.get("meaning") or it.get("translation_en")))
        pool_pl.append(_text(it.get("phrase")  or it.get("transcript_pl")))

    dialogs = []
    for idx, it in enumerate(items, start=1):
        audio = _text(it.get("audio") or it.get("audio_url"))

        tr_pl = _text(it.get("transcript_pl") or it.get("phrase"))
        tr_en = _text(it.get("translation_en") or it.get("meaning"))
        if not tr_pl and tr_en: tr_pl = "—"
        if not tr_en and tr_pl: tr_en = "—"

        gist = it.get("gist") or {}
        gist_prompt = _text(gist.get("prompt")) or "Which best matches the audio?"
        gist_correct = _text(gist.get("correct") or tr_en or tr_pl or "—")
        gist_distractors = gist.get("distractors")
        if not isinstance(gist_distractors, list) or not any(_text(x) for x in gist_distractors):
            gist_distractors = _synth_distractors(gist_correct, [x for x in pool_en if x])

        detail = it.get("detail") or {}
        detail_prompt = _text(detail.get("prompt")) or "What exactly did you hear (in Polish)?"
        detail_correct = _text(detail.get("correct") or tr_pl or "—")
        detail_bank = detail.get("distractor_bank")
        if not isinstance(detail_bank, list) or not any(_text(x) for x in detail_bank):
            detail_bank = _synth_distractors(detail_correct, [x for x in pool_pl if x])

        dialogs.append({
            "id": it.get("id") or f"d{idx:03d}",
            "audio": audio,                    # set-relative key OR absolute URL (audio_url)
            "duration_s": int(it.get("duration_s") or 0),
            "transcript_pl": tr_pl,
            "translation_en": tr_en,
            "gist": {
                "prompt": gist_prompt,
                "correct": gist_correct,
                "distractors": gist_distractors
            },
            "detail": {
                "prompt": detail_prompt,
                "correct": detail_correct,
                "distractor_bank": detail_bank
            }
        })
    return dialogs

def _load_listening_data(set_name: str):
    """Load dialogues.json for a listening set (docs/listening/<set_name>/dialogues.json)."""
    d = PAGES_DIR / "listening" / set_name
    data_path = d / "dialogues.json"
    if not data_path.exists():
        raise FileNotFoundError(f"Missing {data_path}. Create it with your dialogue items.")
    with data_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("dialogues.json must be a JSON array of dialogue objects.")
    return data

# ---------------- R2 manifest helpers ----------------

def _manifest_path(set_name: str) -> Path:
    """Where the per-set manifest lives alongside other static assets."""
    return STATIC_DIR / set_name / "r2_manifest.json"

def _merge_manifest(set_name: str, files_map: dict[str, str], assets_base: str | None) -> Path:
    """
    Merge (or create) docs/static/<set>/r2_manifest.json

    files_map: { "listening/<set>/<file>": "https://cdn.example.com/listening/<set>/<file>", ... }
    """
    mp = _manifest_path(set_name)
    mp.parent.mkdir(parents=True, exist_ok=True)

    existing = {}
    if mp.exists():
        try:
            existing = json.loads(mp.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    if not isinstance(existing, dict):
        existing = {}

    files = existing.get("files") if isinstance(existing.get("files"), dict) else {}
    files.update(files_map)

    merged = {
        "assetsBase": assets_base or existing.get("assetsBase") or "",
        "files": files,
    }
    mp.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return mp

def _cdn_base() -> str | None:
    """
    Prefer an explicit CDN base (e.g., https://cdn.polishpath.com).
    Falls back to public R2 dev domain if provided in env.
    """
    base = os.getenv("R2_CDN_BASE") or os.getenv("R2_PUBLIC_BASE") or ""
    base = base.strip().rstrip("/")
    return base or None

def _publish_listening_audio_to_r2(set_name: str) -> None:
    """
    Upload docs/static/<set>/listening/*.mp3 to R2 under keys:
      listening/<set>/<filename>
    Merge their URLs into r2_manifest.json.
    """
    if not r2_enabled:
        return
    static_dir = STATIC_DIR / set_name / "listening"
    if not static_dir.exists():
        return

    cdn = _cdn_base()
    published: dict[str, str] = {}

    for mp3 in sorted(static_dir.glob("*.mp3")):
        key = f"listening/{set_name}/{mp3.name}"
        try:
            # r2_put_file should accept (local_path, key) and return a URL or None
            url = r2_put_file(mp3, key) or (f"{cdn}/{key}" if cdn else None)
            if url:
                published[key] = url
        except Exception as e:
            print(f"[listen] R2 upload failed for {mp3.name}: {e}")

    if published:
        _merge_manifest(set_name, published, cdn or "")

# ---------------- HTML generation ----------------

def generate_listening_html(set_name: str, data=None):
    """
    Generate docs/listening/<set_name>/index.html with:
      - top site header + weekly gold bar
      - bottom nav
      - Play→Replay with cap
      - 0.75× speed toggle
      - MCQs with safe fallback distractors
      - R2 manifest-aware audio resolution
    """
    out_dir = PAGES_DIR / "listening" / set_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.html"

    if data is None:
        data = _load_listening_data(set_name)

    dialogues = normalize_listening_items(set_name, data)
    dlg_json = json.dumps(dialogues, ensure_ascii=False).replace("</", "<\\/")

    title = f"{_esc(set_name)} • Listening"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root{{ --brand:#2d6cdf; --bg:#0b0c10; --card:#121418; --text:#e9ecf1; --muted:#8b94a7; --border:#1e2230; --good:#2dcf6c; --bad:#ff5a5f; --pad:16px; --radius:14px; --shadow:0 8px 24px rgba(0,0,0,.25); }}
    @media (prefers-color-scheme: light){{ :root{{ --bg:#f7f7fb; --card:#fff; --text:#0c0f14; --muted:#5a6472; --border:#e6e6ef; --shadow:0 8px 24px rgba(0,0,0,.08); }} }}
    *{{ box-sizing:border-box }}
    html,body{{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Inter,system-ui,sans-serif}}
    .wrap{{max-width:900px;margin:0 auto;padding:16px}}
    .card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);padding:20px;margin:16px 0}}
    /* Top site header + gold bar */
    .site-header{{position:sticky;top:0;z-index:20;background:var(--card);border-bottom:1px solid var(--border)}}
    .site-header .row{{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 14px}}
    .brand{{font-weight:800;letter-spacing:.2px}}
    .gold-wrap{{display:flex;align-items:center;gap:8px}}
    .goldbar{{width:140px;height:8px;border-radius:999px;background:rgba(45,108,223,.15);overflow:hidden}}
    .goldbar .fill{{height:100%;width:0;border-radius:999px;background:#2d6cdf;transition:width .25s ease}}
    .gold-label{{font-size:12px;opacity:.8}}

    header.page{{padding:12px 16px}}
    .title{{font-weight:700}}
    .pill{{font-size:.95rem;color:var(--muted)}}

    .player{{display:flex;gap:12px;align-items:center;flex-wrap:wrap}}
    button{{appearance:none;border:0;background:var(--brand);color:#fff;border-radius:12px;padding:10px 14px;font-weight:600;cursor:pointer}}
    button.ghost{{background:transparent;color:var(--text);border:1px solid var(--border)}}
    button[disabled]{{opacity:.5;cursor:not-allowed}}

    .speed-btn{{border:1px solid var(--border);background:var(--card);color:var(--text);border-radius:10px;padding:6px 10px}}
    .speed-btn.active{{background:rgba(45,108,223,.12);color:#2d6cdf;border-color:transparent}}
    .play-btn.replay::before{{content:"↻ ";}}

    .choices{{display:grid;grid-template-columns:1fr;gap:10px;margin-top:10px}}
    .choice{{background:#1a1f27;border:1px solid rgba(128,128,128,.25);padding:12px;border-radius:12px;text-align:left}}
    @media (prefers-color-scheme: light){{ .choice{{background:#fff}} }}
    .choice.correct{{outline:2px solid var(--good)}}
    .choice.wrong{{outline:2px solid var(--bad)}}
    .meta{{display:flex;gap:12px;align-items:center;color:var(--muted);font-size:.95rem}}
    .section-title{{font-weight:700;margin:0 0 6px}}
    .hidden{{display:none}}
    .tr{{white-space:pre-wrap;color:var(--muted)}}
    .footer{{display:flex;justify-content:space-between;align-items:center;margin:12px 0 96px}}

    /* Bottom nav */
    nav.bottom{{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--border);display:flex;justify-content:space-around;padding:6px 8px;gap:8px}}
    nav.bottom a{{flex:1;text-align:center;padding:8px;text-decoration:none;color:var(--text);border-radius:10px;display:flex;flex-direction:column;align-items:center;gap:4px;font-size:12px}}
    nav.bottom a svg{{width:20px;height:20px}}
    nav.bottom a.active{{background:rgba(45,108,223,.12);color:#2d6cdf}}
    @supports(padding: max(0px)){{ nav.bottom{{ padding-bottom: max(6px, env(safe-area-inset-bottom)) }} }}
  </style>
</head>
<body>
  <header class="site-header">
    <div class="row">
      <div class="brand">Path to POLISH</div>
      <div class="gold-wrap">
        <div class="goldbar"><div id="goldFill" class="fill"></div></div>
        <span id="goldLabel" class="gold-label">0 / 500</span>
      </div>
    </div>
  </header>

  <header class="page wrap">
    <div class="title">🎧 Listening • {_esc(set_name)}</div>
    <div class="pill"><span id="gold">0</span> gold • <span id="progress">0/0</span></div>
  </header>

  <main class="wrap">
    <div class="card">
      <div class="meta"><span id="countLabel"></span><span id="lengthLabel"></span><span id="replayLabel"></span></div>
      <div class="player" style="margin-top:8px;">
        <button id="playBtn" class="play-btn" type="button">Play</button>
        <button id="speedBtn" class="speed-btn" type="button" aria-pressed="false" title="Toggle 0.75×">0.75×</button>
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
      <div></div>
      <div class="row"><button id="nextBtn" disabled>Next ▶</button></div>
    </div>

    <div class="card hidden" id="summaryCard">
      <div class="section-title">Session Summary</div>
      <div id="summaryBody"></div>
      <div class="row" style="margin-top:10px;">
        <button id="restartBtn" class="ghost">Restart</button>
        <button id="toHomeBtn">Done</button>
      </div>
    </div>
  </main>

  <!-- Bottom nav -->
  <nav class="bottom">
    <a href="../../index.html">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M3 10.5L12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1v-10.5Z" stroke-width="1.5"/></svg>
      <span>Home</span>
    </a>
    <a href="../../learn.html">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M4 6h16M4 12h16M4 18h9" stroke-width="1.5" stroke-linecap="round"/></svg>
      <span>Learn</span>
    </a>
    <a href="../../manage_sets/">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="4" width="18" height="16" rx="2" ry="2" stroke-width="1.5"/><path d="M7 8h10M7 12h10M7 16h7" stroke-width="1.5" stroke-linecap="round"/></svg>
      <span>Library</span>
    </a>
    <a href="../../dashboard.html">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M4 14h6V4H4v10Zm10 6h6V4h-6v16Z" stroke-width="1.5"/></svg>
      <span>Dashboard</span>
    </a>
    <a href="../../groups.html">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 12a5 5 0 1 0-5-5 5 5 0 0 0 5 5Zm-9 9a9 9 0 0 1 18 0" stroke-width="1.5" stroke-linecap="round"/></svg>
      <span>Groups</span>
    </a>
  </nav>

  <script src="../../static/js/audio-paths.js"></script>

  <script>
  // ---- R2 manifest (if present) ----
  let r2Manifest = null; // {{ files: {{ "listening/<set>/<file>": "https://cdn..." }}, assetsBase }}
  const SET_NAME = {json.dumps(set_name)};
  async function loadR2Manifest(){{
    // Manifest disabled: use local static files only.
    r2Manifest = null;
  }}


  function repoBase(){{
    if (location.hostname === "andrewdionne.github.io") {{
      const parts = location.pathname.split("/").filter(Boolean);
      const repo = parts.length ? parts[0] : "LearnPolish";
      return "/" + repo;
    }}
    return "";
  }}
  function apiFetch(path, init) {{
    // Prefer global api.js helper if present
    if (window.api && typeof window.api.fetch === 'function') {{
      return window.api.fetch(path, init);
    }}
    // Otherwise, try app-config.js (APP_CONFIG.apiBase or APP_CONFIG.API_BASE)
    const base = (window.APP_CONFIG && (APP_CONFIG.apiBase || APP_CONFIG.API_BASE)) || '';
    const prefix = base ? base.replace(/\\/$/, '') : '';
    return fetch(prefix + path, init);
  }}


  function resolveAudioUrl(it) {{
    // 1) absolute URL is honored as-is (audio_url)
    const abs = (it.audio_url || '').trim();
    if (abs && /^(https?:)?\\/\\/|^\\/\\//i.test(abs)) return abs;

    // 2) also honor absolute in `audio` (after normalization/coercion)
    const absAudio = (it.audio || '').trim();
    if (absAudio && /^(https?:)?\\/\\/|^\\/\\//i.test(absAudio)) return absAudio;

    // 3) set-relative static key (e.g., "listening/d001.mp3")
    const rel = (it.audio || '').trim().replace(/^\\/+/, '');
    if (!rel) return '';

    // 4) R2 manifest lookup: listening/<set>/<file>
    const file = rel.split('/').pop();
    const key = `listening/${{SET_NAME}}/${{file}}`;

    if (r2Manifest && r2Manifest.files && r2Manifest.files[key]) return r2Manifest.files[key];
    if (r2Manifest && r2Manifest.assetsBase) {{
      return r2Manifest.assetsBase.replace(/\\/$/, '') + '/' + key;
    }}

    // 5) Fallback to static (GH Pages vs local dev)
    if (location.hostname === "andrewdionne.github.io") {{
      return repoBase() + `/static/${{SET_NAME}}/${{rel}}`;
    }}
    return `/custom_static/${{SET_NAME}}/${{rel}}`;
  }}


  // ---- Config ----
  const CONFIG = {{
    sessionBonus: 20,
    basePerDialogue: 10,
    lengthBonusEverySec: 20,
    lengthBonusCap: 5,
    slowCost: 2,
    replayCost: 1,
    wrongCost: 1,
    replayMax: 3,
    weightGist: 0.4,
    weightDetail: 0.6,
    triesPerQuestion: 3,
  }};

  const DIALOGUES = {dlg_json};

  // ---- State / DOM ----
  const $ = (id) => document.getElementById(id);
  const audioEl = $("audio");
  const playBtn = $("playBtn");
  const speedBtn = $("speedBtn");
  const nextBtn = $("nextBtn");
  const gistCard = $("gistCard"), gistPrompt = $("gistPrompt"), gistChoices = $("gistChoices");
  const detailCard = $("detailCard"), detailPrompt = $("detailPrompt"), detailChoices = $("detailChoices");
  const revealCard = $("revealCard"), plText = $("plText"), enText = $("enText");
  const summaryCard = $("summaryCard"), summaryBody = $("summaryBody");
  const goldLbl = $("gold"), progressLbl = $("progress");
  const countLabel = $("countLabel"), lengthLabel = $("lengthLabel"), replayLabel = $("replayLabel");

  const state = {{
    i: 0, gold: 0, slowOn: false, slowCharged: false,
    replays: 0, answeredGist: false, answeredDetail: false,
    wrongGist: 0, wrongDetail: 0, gistTriesLeft: CONFIG.triesPerQuestion,
    detailTriesLeft: CONFIG.triesPerQuestion, currentDurationS: 0,
    started:false, perDialogueLog:[]
  }};

  // ---- UI helpers ----
  function setHidden(el, h=true){{ el.classList.toggle("hidden", h); }}
  function shuffle(a){{ for(let i=a.length-1;i>0;i--){{const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}} return a; }}

  function setHeader(){{
    goldLbl.textContent = state.gold;
    progressLbl.textContent = `${{state.i+1}}/${{DIALOGUES.length}}`;
    countLabel.textContent = `Dialog ${{state.i+1}} of ${{DIALOGUES.length}}`;
    const dur = (DIALOGUES[state.i]?.duration_s || state.currentDurationS || 0);
    lengthLabel.textContent = dur ? `• ${{dur}}s` : "";
    replayLabel.textContent = `• Replays left: ${{Math.max(0, CONFIG.replayMax - state.replays)}}`;
  }}

  function beginSessionIfNeeded(){{
    if(!state.started){{ state.gold += CONFIG.sessionBonus; state.started = true; goldLbl.textContent = state.gold; }}
  }}

  function loadAudio(it){{
    const src = resolveAudioUrl(it);
    if (!src) {{ console.warn("No audio for item", it); audioEl.removeAttribute("src"); return; }}
    audioEl.src = src;
    audioEl.playbackRate = state.slowOn ? 0.75 : 1.0;
  }}

  function computePool(it){{
    const dur = (it.duration_s || state.currentDurationS || 0);
    const lenBonus = Math.min(CONFIG.lengthBonusCap, Math.floor(dur / CONFIG.lengthBonusEverySec));
    let pool = CONFIG.basePerDialogue + lenBonus;
    if(state.slowCharged) pool -= CONFIG.slowCost;
    pool -= state.replays * CONFIG.replayCost;
    const gShare = pool * CONFIG.weightGist;
    const dShare = pool * CONFIG.weightDetail;
    const gEarn = Math.max(0, Math.floor(gShare - state.wrongGist*CONFIG.wrongCost));
    const dEarn = Math.max(0, Math.floor(dShare - state.wrongDetail*CONFIG.wrongCost));
    return Math.max(0, gEarn + dEarn);
  }}

  function resetPerDialogue(){{
    state.slowOn = false; state.slowCharged = false; speedBtn.classList.remove('active'); speedBtn.textContent='0.75×'; speedBtn.setAttribute('aria-pressed','false');
    state.replays = 0; state.answeredGist = false; state.answeredDetail = false;
    state.wrongGist = 0; state.wrongDetail = 0;
    state.gistTriesLeft = CONFIG.triesPerQuestion; state.detailTriesLeft = CONFIG.triesPerQuestion;
    state.currentDurationS = 0;
    nextBtn.disabled = true;
    gistChoices.innerHTML = ""; detailChoices.innerHTML = "";
    setHidden(gistCard,true); setHidden(detailCard,true); setHidden(revealCard,true);
  }}

  function startDialogue(idx){{
    if(idx >= DIALOGUES.length) return endSession();
    resetPerDialogue();
    const it = DIALOGUES[idx];
    state.currentDurationS = Math.round(it?.duration_s||0);
    setHeader();
    loadAudio(it);
    playBtn.classList.remove('replay'); playBtn.textContent = 'Play';
  }}

  function endSession(){{
    setHidden(gistCard,true); setHidden(detailCard,true); setHidden(revealCard,true);
    setHidden(summaryCard,false);
    const rows = state.perDialogueLog.map((r,k)=>`#${{k+1}} • +${{r.payout}} gold • replay:${{r.replays}} • slow:${{r.slow?'y':'n'}} • gist×${{r.wrongGist}} • detail×${{r.wrongDetail}}`).join("\\n");
    summaryBody.textContent = `Total gold: ${{state.gold}}\\n\\n${{rows}}`;
  }}

  function renderGist(it){{
    const g = it.gist || {{}};
    setHidden(gistCard,false);
    gistPrompt.textContent = g.prompt || "Which best matches the audio?";
    const opts = shuffle([ g.correct, ...(g.distractors||[]).slice(0,3) ]);
    gistChoices.innerHTML = "";
    opts.forEach(txt=>{{
      const b = document.createElement('button');
      b.className='choice'; b.textContent = txt || "—";
      b.onclick = ()=> onGistAnswer(it, b, txt === g.correct);
      gistChoices.appendChild(b);
    }});
  }}

  function renderDetail(it){{
    const d = it.detail || {{}};
    setHidden(detailCard,false);
    detailPrompt.textContent = d.prompt || "What exactly did you hear (in Polish)?";
    const bank = (d.distractor_bank||[]).filter(x=>x && x!==d.correct);
    const opts = shuffle([ d.correct, ...bank.slice(0,3) ]);
    detailChoices.innerHTML = "";
    opts.forEach(txt=>{{
      const b = document.createElement('button');
      b.className='choice'; b.textContent = txt || "—";
      b.onclick = ()=> onDetailAnswer(it, b, txt === d.correct);
      detailChoices.appendChild(b);
    }});
  }}

  function lockButtons(containerId){{ [...document.getElementById(containerId).children].forEach(c=>c.disabled=true); }}

  function onGistAnswer(it, btn, ok){{
    if(state.answeredGist) return;
    if(ok){{ btn.classList.add('correct'); state.answeredGist=true; lockButtons('gistChoices'); if(!state.answeredDetail) renderDetail(it); if(state.answeredDetail) finalize(it); }}
    else {{
      btn.classList.add('wrong'); btn.disabled=true; state.wrongGist++; state.gistTriesLeft--;
      if(state.gistTriesLeft<=0){{ state.answeredGist=true; [...gistChoices.children].forEach(c=>{{ if(c.textContent==(it.gist?.correct||'')) c.classList.add('correct'); c.disabled=true; }}); if(!state.answeredDetail) renderDetail(it); if(state.answeredDetail) finalize(it); }}
    }}
  }}

  function onDetailAnswer(it, btn, ok){{
    if(state.answeredDetail) return;
    if(ok){{ btn.classList.add('correct'); state.answeredDetail=true; lockButtons('detailChoices'); if(state.answeredGist) finalize(it); }}
    else {{
      btn.classList.add('wrong'); btn.disabled=true; state.wrongDetail++; state.detailTriesLeft--;
      if(state.detailTriesLeft<=0){{ state.answeredDetail=true; [...detailChoices.children].forEach(c=>{{ if(c.textContent==(it.detail?.correct||'')) c.classList.add('correct'); c.disabled=true; }}); if(state.answeredGist) finalize(it); }}
    }}
  }}

  function finalize(it){{
    const gained = computePool(it);
    state.gold += gained;
    state.perDialogueLog.push({{
      id: it.id||`d${{state.i+1}}`,
      slow: state.slowCharged, replays: state.replays,
      wrongGist: state.wrongGist, wrongDetail: state.wrongDetail,
      payout: gained, duration_s: it.duration_s || state.currentDurationS || 0
    }});
    goldLbl.textContent = state.gold;
    plText.textContent = it.transcript_pl || "(no transcript)";
    enText.textContent = it.translation_en || "";
    setHidden(revealCard,false);
    nextBtn.disabled = false;
  }}

  // ---- Controls ----
  (function wirePlayReplay(){{
    let hasPlayed=false;
    playBtn.addEventListener('click', ()=>{{
      beginSessionIfNeeded();
      if(hasPlayed){{
        if(state.replays >= CONFIG.replayMax) return;
        state.replays++;
        setHeader();
      }}
      audioEl.currentTime = 0;
      audioEl.play().catch(()=>{{}});
    }});
    audioEl.addEventListener('play', ()=>{{
      if(!hasPlayed){{
        hasPlayed = true;
        playBtn.classList.add('replay');
        playBtn.textContent = 'Replay';
      }}
    }});
    audioEl.addEventListener('ended', ()=>{{ renderGist(DIALOGUES[state.i]); }});
    audioEl.addEventListener('loadedmetadata', ()=>{{
      const d = isFinite(audioEl.duration) ? Math.round(audioEl.duration) : 0;
      if(d>0) state.currentDurationS = d;
      setHeader();
    }});
  }})();

  (function wireSpeed(){{
    function apply(){{
      audioEl.playbackRate = state.slowOn ? 0.75 : 1.0;
      speedBtn.classList.toggle('active', state.slowOn);
      speedBtn.setAttribute('aria-pressed', state.slowOn ? 'true' : 'false');
      speedBtn.textContent = state.slowOn ? '1.0×' : '0.75×';
      speedBtn.title = state.slowOn ? 'Back to 0.75×' : 'Switch to 0.75×';
    }}
    speedBtn.addEventListener('click', ()=>{{
      if(!state.slowOn && !state.slowCharged) state.slowCharged = true;
      state.slowOn = !state.slowOn; apply();
    }});
    apply();
  }})();

  nextBtn.onclick = ()=>{{ state.i++; if(state.i >= DIALOGUES.length) endSession(); else startDialogue(state.i); }};
  $("toHomeBtn").onclick = ()=>{{ location.href='../../index.html'; }};
  $("restartBtn").onclick = ()=>{{ location.reload(); }};

  // gold bar (if token present)
  (async function wireGold() {{
    try {{
      const t = localStorage.getItem('lp_token') || '';
      if (!t) return;
      const r = await apiFetch('/api/my/stats', {{ headers: {{ Authorization: 'Bearer ' + t }} }});
      if (!r.ok) return;
      const s = await r.json();
      const got = Number(s.weekly_gold || s.weekly_points || 0);
      const goal = Number(s.goal_gold || s.goal_points || 500) || 500;
      const pct = Math.max(0, Math.min(100, Math.round((got / goal) * 100)));
      const fill = document.getElementById('goldFill');
      const lab  = document.getElementById('goldLabel');
      if (fill) fill.style.width = pct + '%';
      if (lab)  lab.textContent = `${{got}} / ${{goal}}`;
    }} catch (_err) {{
      /* no-op */
    }}
  }})();


  // mount
  (async function init(){{
    await loadR2Manifest();
    if(!Array.isArray(DIALOGUES) || !DIALOGUES.length){{
      document.body.innerHTML = '<div style="padding:20px;font-family:sans-serif;">⚠️ No dialogues found for this set.</div>';
      return;
    }}
    startDialogue(0);
  }})();
  </script>
</body>
</html>"""

    out_path.write_text(html, encoding="utf-8")
    print(f"✅ listening page generated: {out_path}")
    return out_path

# ====== Creation helpers: coerce, synthesize audio, publish to R2, regenerate HTML ======

def _is_dialogues_format(items):
    """Treat as authored dialogues only if MCQ fields exist; otherwise coerce."""
    try:
        first = items[0]
    except Exception:
        return False
    return isinstance(first, dict) and (("gist" in first) or ("detail" in first))

def _coerce_simple_listen_to_dialogues(items):
    """Convert flat items into dialogues with MCQs."""
    phrases = [str(x.get("phrase") or x.get("polish") or "").strip() for x in items]
    meanings = [str(x.get("meaning") or x.get("english") or "").strip() for x in items]
    fallback_meaning = [
        "A greeting", "An apology", "A request", "A question",
        "Directions", "Small talk", "A number", "A time of day",
    ]

    out = []
    for idx, it in enumerate(items, start=1):
        audio = it.get("audio") or it.get("audio_url") or ""
        pl = str(it.get("phrase") or it.get("polish") or "").strip()
        en = str(it.get("meaning") or it.get("english") or "").strip()

        other_meanings = [m for m in meanings if m and m != en]
        random.shuffle(other_meanings)
        gist_distractors = other_meanings[:3]
        if len(gist_distractors) < 3:
            pool = [x for x in fallback_meaning if x != en]
            random.shuffle(pool)
            gist_distractors += pool[: 3 - len(gist_distractors)]

        other_phrases = [p for p in phrases if p and p != pl]
        random.shuffle(other_phrases)
        bank = other_phrases[:10]

        if not pl: pl = en or "—"
        if not en: en = pl or "—"

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
    """Write meta.json + dialogues.json for a listening set (coercing if needed)."""
    base = PAGES_DIR / "listening" / set_name
    base.mkdir(parents=True, exist_ok=True)
    dialogues = items if _is_dialogues_format(items) else _coerce_simple_listen_to_dialogues(items)
    meta = {
        "set_name": set_name,
        "description": "Auto-generated listening set (can be edited).",
        "tags": ["listening"],
        "recommended_session_size": min(10, len(dialogues) or 10),
        "advanced_mode_available": False,
        "distractor_bank_policy": "Detail draws 3 from a bank each run."
    }
    (base / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (base / "dialogues.json").write_text(json.dumps(dialogues, ensure_ascii=False, indent=2), encoding="utf-8")
    return base

def render_missing_audio_for_listening(set_name: str, voice_lang: str = "pl"):
    """
    For each dialogue in docs/listening/<set>/dialogues.json:
      - If 'audio_url' is present, leave as-is.
      - Else synthesize MP3 from transcript_pl/detail.correct/translation_en
        into docs/static/<set>/listening/dXXX.mp3,
        set item["audio"] = "listening/dXXX.mp3",
        and try to upload to R2 (item["audio_url"] on success).
    """
    # TTS helper is imported at module level as _tts_to_mp3
    cdn = _cdn_base()


    base = PAGES_DIR / "listening" / set_name
    dlg_path = base / "dialogues.json"
    if not dlg_path.exists():
        raise FileNotFoundError(f"Missing {dlg_path}")

    try:
        dialogues = json.loads(dlg_path.read_text(encoding="utf-8"))
        if not isinstance(dialogues, list):
            raise ValueError("dialogues.json must be a JSON array.")
    except Exception as e:
        raise ValueError(f"Invalid dialogues.json: {e}")

    static_dir = STATIC_DIR / set_name / "listening"
    static_dir.mkdir(parents=True, exist_ok=True)

    # Collect CDN mappings for an optional r2_manifest.json
    r2_map: dict[str, str] = {}

    changed = False
    for idx, item in enumerate(dialogues, start=1):
        # If already points to a remote URL, keep it
        audio_url = (item.get("audio_url") or "").strip()
        if audio_url.startswith("http://") or audio_url.startswith("https://"):
            continue

        # If we have a local relative audio path and the file exists, keep (but may still upload)
        existing_rel = (item.get("audio") or "").strip()  # e.g., 'listening/d001.mp3'
        if existing_rel:
          candidate = STATIC_DIR / set_name / existing_rel
          if candidate.exists():
              # Upload existing file if possible (use consistent key space)
              if r2_enabled and r2_put_file and "audio_url" not in item:
                  try:
                      fname = candidate.name
                      r2_key = f"listening/{set_name}/{fname}"
                      url = r2_put_file(candidate, r2_key) or (f"{cdn}/{r2_key}" if cdn else None)
                      if url:
                          item["audio_url"] = url
                          r2_map[r2_key] = url
                          changed = True
                  except Exception as e:
                      print(f"[listen] R2 upload failed for existing {existing_rel}: {e}")
          continue  # no need to synthesize


        # Choose text to synthesize
        text = (
            (item.get("transcript_pl") or "").strip()
            or (item.get("detail", {}).get("correct") or "").strip()
            or (item.get("translation_en") or "").strip()
        )
        if not text:
            # Nothing to synthesize; leave item as-is
            continue

        # Render MP3 locally (Azure→gTTS helper)
        filename = f"d{idx:03d}.mp3"
        out_path = static_dir / filename
        try:
            if not out_path.exists():
                ok = _tts_to_mp3(text, out_path)  # voice is chosen inside helper/env
                if not ok:
                    raise RuntimeError("TTS failed")
        except Exception as e:
            print(f"[listen] TTS failed for {set_name} #{idx}: {e}")
            continue


        # Always set local relative path for dev/offline
        item["audio"] = f"listening/{filename}"
        changed = True

        # Upload to R2 and expose a CDN URL if possible
        if r2_enabled and r2_put_file:
            try:
                r2_key = f"listening/{set_name}/{filename}"
                url = r2_put_file(out_path, r2_key) or (f"{cdn}/{r2_key}" if cdn else None)
                if url:
                    item["audio_url"] = url
                    r2_map[r2_key] = url
            except Exception as e:
                print(f"[listen] R2 upload failed for {filename}: {e}")

    # Persist updated dialogues
    if changed:
        dlg_path.write_text(json.dumps(dialogues, ensure_ascii=False, indent=2), encoding="utf-8")

    # Merge/update manifest (keys like 'listening/<set>/<file>')
    if r2_map:
        try:
            _merge_manifest(set_name, r2_map, cdn or "")
        except Exception as e:
            print(f"[listen] Failed to write r2_manifest.json: {e}")

    return changed


def create_listening_set(set_name: str, items):
    """
    Create listening set:
      1) Write meta.json & dialogues.json (coerce if needed)
      2) Render missing audio to docs/static/<set>/listening/
      3) Upload audio to R2 (if configured) and merge r2_manifest.json
      4) Generate HTML page
    """
    out_dir = save_listening_set(set_name, items)

    # Render MP3s into docs/static/<set>/listening and rewrite 'audio' fields
    try:
        render_missing_audio_for_listening(set_name)
    except Exception as e:
        print(f"[listen] prerender skipped/failed for {set_name}: {e}")

    # Publish to R2 + manifest merge (no-op if r2 not configured)
    try:
        _publish_listening_audio_to_r2(set_name)
    except Exception as e:
        print(f"[listen] R2 publish skipped/failed for {set_name}: {e}")

    # Regenerate HTML using the (possibly updated) dialogues
    with (out_dir / "dialogues.json").open("r", encoding="utf-8") as f:
        dialogues = json.load(f)
    return generate_listening_html(set_name, dialogues)
