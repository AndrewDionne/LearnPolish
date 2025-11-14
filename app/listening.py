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
    Generate docs/listening/<set_name>/index.html and sw.js.

    UI/UX:
      - Dual-host <base> (GH Pages vs Flask), topbar/page-chrome, bottom nav
      - Player: Play/Replay, 0.75× toggle, length display, replay cap
      - MCQs: Gist + Detail with stable shuffles, tries, earned gold
      - Transcript reveal after answering
      - R2 manifest-aware audio resolution via AudioPaths.resolveListening
      - Offline caching buttons (⬇️ Offline / 🗑 Remove), cache-first SW
      - Performance: manifest prefetch, preloading current+next audio,
        canplaythrough gating, minimal DOM churn
    """
    out_dir = PAGES_DIR / "listening" / set_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.html"

    if data is None:
        data = _load_listening_data(set_name)

    dialogues = normalize_listening_items(set_name, data)
    dlg_json = json.dumps(dialogues, ensure_ascii=False).replace(r"</", r"<\/")

    title = f"Listening • {_esc(set_name)} • Path to POLISH"

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

  <title>{title}</title>
  <link rel="stylesheet" href="static/app.css?v=5" />
  <link rel="icon" type="image/svg+xml" href="../../static/brand.svg" />

  <style>
    .wrap{{ max-width:900px; margin:0 auto 92px; padding:0 16px; }}
    .stack{{ display:grid; gap:16px }}
    .row{{ display:flex; align-items:center; gap:10px; flex-wrap:wrap }}
    .card{{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:16px }}

    .toolbar .btn{{ display:inline-flex; align-items:center; gap:8px; padding:10px 14px; border-radius:10px;
      border:1px solid var(--border); background:var(--card); cursor:pointer }}
    .btn-primary{{ background:var(--brand); border-color:var(--brand); color:#fff }}
    .btn:disabled{{ opacity:.6; cursor:default }}

    .meta{{ color:var(--muted); font-size:.95rem }}
    .section-title{{ font-weight:700; margin:0 0 6px }}

    .player{{ display:flex; gap:12px; align-items:center; flex-wrap:wrap }}
    .speed-btn{{ border:1px solid var(--border); background:var(--card); color:var(--text); border-radius:10px; padding:6px 10px }}
    .speed-btn.active{{ background:rgba(45,108,223,.12); color:#2d6cdf; border-color:transparent }}
    .play-btn.replay::before{{ content:"↻ "; }}

    .choices{{ display:grid; grid-template-columns:1fr; gap:10px; margin-top:10px }}
    .choice{{ background:var(--card); border:1px solid var(--border); padding:12px; border-radius:12px; text-align:left }}
    .choice.correct{{ outline:2px solid var(--gold) }}
    .choice.wrong{{ outline:2px solid #ff5a5f }}

    .tr{{ white-space:pre-wrap; color:var(--muted) }}
    .footer{{ display:flex; justify-content:space-between; align-items:center; margin:12px 0 0 }}
    .hidden{{ display:none }}

    /* Debug overlay (toggle via ?debug=1) */
    #dbg{{ display:none; position:fixed; bottom:8px; left:8px; right:8px; max-height:44vh; overflow:auto;
      background:#000; color:#0f0; padding:8px 10px; border-radius:10px; font-family:ui-monospace, Menlo, monospace;
      font-size:12px; white-space:pre-wrap; z-index:9999 }}
  </style>
</head>
<body
  data-header="Path to Polish"
  data-note-lead="Listening"
  data-note-tail="{_esc(set_name)}"
  style="--logo-size:40px; --banner-size:24px; --banner-size-lg:30px">

  <!-- Header (brand + auth) -->
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

  <!-- Tight page note -->
  <div class="wrap page-note-wrap">
    <div id="pageNote" class="page-note"></div>
  </div>

  <!-- Main -->
  <main class="wrap stack">
    <section class="card">
      <div class="row toolbar">
        <div id="countLabel" class="meta">Dialog 1</div>
        <div id="lengthLabel" class="meta"></div>
        <div id="replayLabel" class="meta"></div>
        <div style="flex:1"></div>
        <button id="btnOffline" class="btn">⬇️ Offline</button>
        <button id="btnOfflineRm" class="btn" style="display:none;">🗑 Remove</button>
      </div>

      <div class="player" style="margin-top:8px;">
        <button id="playBtn" class="play-btn btn btn-primary" type="button">Play</button>
        <button id="speedBtn" class="speed-btn" type="button" aria-pressed="false" title="Toggle 0.75×">0.75×</button>
        <audio id="audio" preload="auto"></audio>
      </div>
      <div id="offlineStatus" class="meta" style="margin-top:6px"></div>
    </section>

    <section class="card" id="gistCard" aria-live="polite">
      <div class="section-title">Gist</div>
      <div id="gistPrompt"></div>
      <div class="choices" id="gistChoices"></div>
    </section>

    <section class="card" id="detailCard" aria-live="polite">
      <div class="section-title">Details</div>
      <div id="detailPrompt"></div>
      <div class="choices" id="detailChoices"></div>
    </section>

    <section class="card" id="revealCard">
      <div class="section-title">Transcript</div>
      <div class="tr" id="plText"></div>
      <div style="height:6px"></div>
      <div class="section-title">English</div>
      <div class="tr" id="enText"></div>
    </section>

    <section class="footer">
      <div class="meta"><b id="gold">0</b> gold • <span id="progress">0/0</span></div>
      <div class="row"><button id="nextBtn" class="btn" disabled>Next ▶</button></div>
    </section>

    <section class="card hidden" id="summaryCard">
      <div class="section-title">Session Summary</div>
      <div id="summaryBody" style="white-space:pre-wrap"></div>
      <div class="row" style="margin-top:10px;">
        <button id="restartBtn" class="btn">Restart</button>
        <button id="toHomeBtn" class="btn btn-primary">Done</button>
      </div>
    </section>
  </main>

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

  <script>
    // ---------- Data / State ----------
    const SET_NAME = {json.dumps(set_name)};
    const DIALOGUES = {dlg_json};

    let r2Manifest = null;
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
    const offlineStatus = $("offlineStatus");

    const state = {{
      i: 0,
      gold: 0,
      slowOn: false,
      slowCharged: false,
      replays: 0,
      answeredGist: false,
      answeredDetail: false,
      wrongGist: 0,
      wrongDetail: 0,
      gistTriesLeft: 3,
      detailTriesLeft: 3,
      currentDurationS: 0,
      started:false,
      perDialogueLog:[],
      preloaded: Object.create(null)  // index -> HTMLAudioElement
    }};

    // ---------- Helpers ----------
    function setHidden(el, h=true){{ el.classList.toggle("hidden", h); }}
    function shuffleStable(arr){{
      // Stable shuffle by seeding with dialog index to keep answers consistent per load
      const seed = (state.i+1) * 9301 + 49297; // simple LCG seed
      let a = arr.slice();
      let s = seed;
      for (let i=a.length-1;i>0;i--) {{
        s = (s * 1103515245 + 12345) & 0x7fffffff;
        const j = s % (i+1);
        [a[i],a[j]] = [a[j],a[i]];
      }}
      return a;
    }}
    function updateHeader(){{
      goldLbl.textContent = state.gold;
      progressLbl.textContent = `${{state.i+1}}/${{DIALOGUES.length}}`;
      countLabel.textContent = `Dialog ${{state.i+1}} of ${{DIALOGUES.length}}`;
      const dur = (DIALOGUES[state.i]?.duration_s || state.currentDurationS || 0);
      lengthLabel.textContent = dur ? `• ${{dur}}s` : "";
      replayLabel.textContent = `• Replays left: ${{Math.max(0, 3 - state.replays)}}`;
    }}
    function beginSessionIfNeeded(){{
      if(!state.started){{ state.gold += 20; state.started = true; goldLbl.textContent = state.gold; }}
    }}

    // ---------- Audio paths / manifest ----------
    async function loadManifest(){{
      try {{ r2Manifest = await AudioPaths.fetchManifest(SET_NAME); }} catch(_e) {{ r2Manifest = null; }}
    }}
    function resolveAudio(it){{
      try {{ return AudioPaths.resolveListening(SET_NAME, it, r2Manifest); }}
      catch(_e) {{ return ""; }}
    }}

    // ---------- Preloading (speed-up) ----------
    function preloadAudio(idx){{
      if (state.preloaded[idx]) return;
      const it = DIALOGUES[idx];
      if (!it) return;
      const src = resolveAudio(it);
      if (!src) return;
      const a = new Audio();
      a.preload = 'auto';
      a.src = src;
      // Trigger download; catch to avoid autoplay warnings
      a.load();
      state.preloaded[idx] = a;
    }}

    // ---------- Scoring / gold ----------
    function computePayout(it){{
      const dur = (it.duration_s || state.currentDurationS || 0);
      const lenBonus = Math.min(5, Math.floor(dur / 20));  // +1 per 20s, cap 5
      let pool = 10 + lenBonus;
      if(state.slowCharged) pool -= 2;
      pool -= state.replays * 1;
      const gShare = pool * 0.4;
      const dShare = pool * 0.6;
      const gEarn = Math.max(0, Math.floor(gShare - state.wrongGist*1));
      const dEarn = Math.max(0, Math.floor(dShare - state.wrongDetail*1));
      return Math.max(0, gEarn + dEarn);
    }}

    function resetPerDialogue(){{
      state.slowOn = false; state.slowCharged = false;
      speedBtn.classList.remove('active'); speedBtn.textContent='0.75×'; speedBtn.setAttribute('aria-pressed','false');
      state.replays = 0; state.answeredGist = false; state.answeredDetail = false;
      state.wrongGist = 0; state.wrongDetail = 0;
      state.gistTriesLeft = 3; state.detailTriesLeft = 3;
      state.currentDurationS = 0;
      nextBtn.disabled = true;
      gistChoices.innerHTML = ""; detailChoices.innerHTML = "";
      setHidden(gistCard,true); setHidden(detailCard,true); setHidden(revealCard,true);
    }}

    function startDialogue(idx){{
      if(idx >= DIALOGUES.length) return endSession();
      resetPerDialogue();
      const it = DIALOGUES[idx];

      // Prefer preloaded element if present; fallback to set src directly
      const pre = state.preloaded[idx];
      if (pre) {{
        // Rebind the preloaded element into place to keep events
        audioEl.src = pre.src;
      }} else {{
        audioEl.src = resolveAudio(it) || '';
      }}

      audioEl.playbackRate = state.slowOn ? 0.75 : 1.0;
      playBtn.classList.remove('replay'); playBtn.textContent = 'Play';

      // Preload NEXT in idle time
      (window.requestIdleCallback || window.setTimeout)(()=> preloadAudio(idx+1), 50);
      updateHeader();
    }}

    async function endSession(){{
      // 1) Try posting score (safe if token present; ignore errors)
      try{{
        await api.requireAuth('../../login.html');
        const details = {{ perDialogueLog: state.perDialogueLog, total_gold: state.gold }};
        await api.fetch('/api/submit_score', {{
          method:'POST',
          headers:{{'Content-Type':'application/json'}},
          body: JSON.stringify({{
            set_name: SET_NAME,
            mode: 'listening',
            score: Math.max(0, Math.round(state.gold||0)),
            attempts: 1,
            details
          }})
        }});
      }}catch(_){{}}

      // 2) Persist a lightweight lastResult for summary.html (optional)
      try {{
        sessionStorage.setItem('lp.lastResult', JSON.stringify({{
          set: SET_NAME, mode: 'listening', score: Math.max(0, Math.round(state.gold||0))
        }}));
      }} catch(_){{}}

      // 3) Redirect to unified summary page (it will also fetch weekly/streak)
      location.href = '../../summary.html'
        + '?set='  + encodeURIComponent(SET_NAME)
        + '&mode=' + 'listening'
        + '&score='+ encodeURIComponent(Math.max(0, Math.round(state.gold||0)));
    }}



    // ---------- MCQs ----------
    function renderGist(it){{
      setHidden(gistCard,false);
      const g = it.gist || {{}};
      gistPrompt.textContent = g.prompt || "Which best matches the audio?";
      const opts = shuffleStable([ g.correct, ...(g.distractors||[]).slice(0,3) ]);
      gistChoices.innerHTML = "";
      for (const txt of opts) {{
        const b = document.createElement('button');
        b.className='choice'; b.textContent = txt || "—";
        b.onclick = ()=> onGist(it, b, txt === g.correct);
        gistChoices.appendChild(b);
      }}
    }}
    function renderDetail(it){{
      setHidden(detailCard,false);
      const d = it.detail || {{}};
      detailPrompt.textContent = d.prompt || "What exactly did you hear (in Polish)?";
      const bank = (d.distractor_bank||[]).filter(x=>x && x!==d.correct);
      const opts = shuffleStable([ d.correct, ...bank.slice(0,3) ]);
      detailChoices.innerHTML = "";
      for (const txt of opts) {{
        const b = document.createElement('button');
        b.className='choice'; b.textContent = txt || "—";
        b.onclick = ()=> onDetail(it, b, txt === d.correct);
        detailChoices.appendChild(b);
      }}
    }}
    function lockButtons(el){{ [...el.children].forEach(c=>c.disabled=true); }}

    function onGist(it, btn, ok){{
      if(state.answeredGist) return;
      if(ok){{
        btn.classList.add('correct'); state.answeredGist=true; lockButtons(gistChoices);
        if(!state.answeredDetail) renderDetail(it);
        if(state.answeredDetail) finalize(it);
      }} else {{
        btn.classList.add('wrong'); btn.disabled=true; state.wrongGist++; state.gistTriesLeft--;
        if(state.gistTriesLeft<=0){{
          state.answeredGist=true;
          [...gistChoices.children].forEach(c=>{{ if(c.textContent==(it.gist?.correct||'')) c.classList.add('correct'); c.disabled=true; }});
          if(!state.answeredDetail) renderDetail(it);
          if(state.answeredDetail) finalize(it);
        }}
      }}
    }}
    function onDetail(it, btn, ok){{
      if(state.answeredDetail) return;
      if(ok){{
        btn.classList.add('correct'); state.answeredDetail=true; lockButtons(detailChoices);
        if(state.answeredGist) finalize(it);
      }} else {{
        btn.classList.add('wrong'); btn.disabled=true; state.wrongDetail++; state.detailTriesLeft--;
        if(state.detailTriesLeft<=0){{
          state.answeredDetail=true;
          [...detailChoices.children].forEach(c=>{{ if(c.textContent==(it.detail?.correct||'')) c.classList.add('correct'); c.disabled=true; }});
          if(state.answeredGist) finalize(it);
        }}
      }}
    }}

    function finalize(it){{
      const gained = computePayout(it);
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

    // ---------- Controls ----------
    (function wirePlayReplay(){{
      let hasPlayed=false;

      playBtn.addEventListener('click', ()=>{{
        beginSessionIfNeeded();
        if(hasPlayed){{
          if(state.replays >= 3) return;
          state.replays++; updateHeader();
        }}
        // Prefer preloaded element for seek/play
        const pre = state.preloaded[state.i];
        if (pre && pre.src === audioEl.src) {{
          pre.currentTime = 0; pre.playbackRate = audioEl.playbackRate;
          pre.play().catch(()=>{{}});
          // keep audioEl as the canonical element for events
          // mirror duration from preloaded
          if (isFinite(pre.duration)) state.currentDurationS = Math.round(pre.duration);
        }} else {{
          audioEl.currentTime = 0;
          audioEl.play().catch(()=>{{}});
        }}
      }});

      audioEl.addEventListener('play', ()=>{{
        if(!hasPlayed){{
          hasPlayed = true;
          playBtn.classList.add('replay');
          playBtn.textContent = 'Replay';
        }}
      }});

      audioEl.addEventListener('canplaythrough', ()=>{{
        if (isFinite(audioEl.duration) && audioEl.duration>0) {{
          state.currentDurationS = Math.round(audioEl.duration);
          updateHeader();
        }}
      }});

      audioEl.addEventListener('ended', ()=>{{ renderGist(DIALOGUES[state.i]); }});
      audioEl.addEventListener('loadedmetadata', ()=>{{
        const d = isFinite(audioEl.duration) ? Math.round(audioEl.duration) : 0;
        if(d>0) state.currentDurationS = d;
        updateHeader();
      }});
      audioEl.addEventListener('error', ()=>{{
        offlineStatus.textContent = "🔇 Audio failed to load.";
      }});
    }})();

    (function wireSpeed(){{
      function apply(){{
        audioEl.playbackRate = state.slowOn ? 0.75 : 1.0;
        const pre = state.preloaded[state.i]; if (pre) pre.playbackRate = audioEl.playbackRate;
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
    $("toHomeBtn").onclick = ()=>{{ location.href='index.html'; }};
    $("restartBtn").onclick = ()=>{{ location.reload(); }};

    // ---------- Offline SW ----------
    function listeningUrls(){{
      const urls = [];
      for (let i=0;i<DIALOGUES.length;i++){{
        try {{ urls.push(AudioPaths.resolveListening(SET_NAME, DIALOGUES[i], r2Manifest)); }} catch(_){{
        }}
      }}
      return Array.from(new Set(urls.filter(Boolean)));
    }}
    async function ensureSW(){{
      if (!('serviceWorker' in navigator)) return null;
      try {{
        const reg = await navigator.serviceWorker.register('./sw.js', {{ scope:'./' }});
        await navigator.serviceWorker.ready;
        return reg;
      }} catch(e) {{
        offlineStatus.textContent = '❌ Offline not available.';
        return null;
      }}
    }}
    $("btnOffline").addEventListener('click', async ()=>{{
      const reg = await ensureSW();
      if (!reg || !reg.active) return;
      offlineStatus.textContent = '⬇️ Downloading…';
      reg.active.postMessage({{ type:'CACHE_SET', cache:`listening-{set_name}`, urls: listeningUrls() }});
    }});
    $("btnOfflineRm").addEventListener('click', async ()=>{{
      const reg = await ensureSW(); if (!reg || !reg.active) return;
      reg.active.postMessage({{ type:'UNCACHE_SET', cache:`listening-{set_name}` }});
    }});
    navigator.serviceWorker?.addEventListener('message', (ev) => {{
      const d = ev.data || {{}};
      if (d.type === 'CACHE_PROGRESS') {{
        offlineStatus.textContent = `⬇️ ${{d.done}} / ${{d.total}} files cached…`;
      }} else if (d.type === 'CACHE_DONE') {{
        offlineStatus.textContent = "✅ Available offline";
        $("btnOfflineRm").style.display = "inline-flex";
      }} else if (d.type === 'UNCACHE_DONE') {{
        offlineStatus.textContent = "🗑 Removed offline copy";
        $("btnOfflineRm").style.display = "none";
      }} else if (d.type === 'CACHE_ERROR') {{
        offlineStatus.textContent = "❌ Offline failed";
      }}
    }});

    // ---------- Auth chrome ----------
    (async () => {{
      await api.requireAuth('login.html');
      const logoutBtn   = document.getElementById('logoutBtn');
      const loginLink   = document.getElementById('loginLink');
      const registerLink= document.getElementById('registerLink');
      try {{
        const r = await api.fetch('/api/me');
        if (r.ok) {{
          loginLink.style.display='none';
          registerLink.style.display='none';
          logoutBtn.style.display='inline-flex';
        }}
      }} catch(_){{
      }}
      logoutBtn?.addEventListener('click', async ()=>{{
        try {{ await api.fetch('/api/logout',{{method:'POST'}}); }} catch(_){{
        }}
        api.clearToken(); location.href='login.html';
      }});
    }})();

    // ---------- Init ----------
    (async function init(){{
      if (!Array.isArray(DIALOGUES) || !DIALOGUES.length){{
        document.body.innerHTML = '<div class="wrap" style="padding:20px;">⚠️ No dialogues found for this set.</div>';
        return;
      }}
      await loadManifest();
      // Preload first two audios to reduce first-click latency
      preloadAudio(0); preloadAudio(1);
      startDialogue(0);
    }})();

    // Housekeeping
    window.addEventListener('beforeunload', ()=>{{
      try {{ for (const k in state.preloaded) {{ const a = state.preloaded[k]; a && a.pause && a.pause(); }} }} catch(_){{
      }}
    }});
  </script>
</body>
</html>"""

    out_path.write_text(html, encoding="utf-8")

    # --- Service worker for offline listening audio ---
    sw_js = """/* listening SW */
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
    const cacheName = data.cache || 'listening-cache';
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
    const cacheName = data.cache || 'listening-cache';
    await caches.delete(cacheName);
    client && client.postMessage({ type: 'UNCACHE_DONE', cache: cacheName });
  }
});

// Cache-first if present; fall through to network
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
