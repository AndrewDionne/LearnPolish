# app/sets_utils.py
import json
import re
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from .constants import (
    PAGES_DIR, SETS_DIR, STATIC_DIR, SET_MODES_JSON, SYSTEM_CUE_NAMES
)
from .utils import asset_url  # builds full CDN URL from a key (uses Config.R2_CDN_BASE)
# --- Normalization helpers ---------------------------------------------------
def _norm_str(x) -> str:
    return str(x or "").strip()

def normalize_cards(data: list[dict]) -> list[dict]:
    """
    Canonical for flashcards/practice:
      { "phrase": str, "meaning": str, "pronunciation"?: str, "audio"?: str | "audio_url"?: str }
    Accept synonyms: phrase|polish|front, meaning|english|back, pronunciation|pron.
    Deduplicates by (phrase, meaning).
    """
    out, seen = [], set()
    for it in data or []:
        phrase  = _norm_str(it.get("phrase")  or it.get("polish") or it.get("front"))
        meaning = _norm_str(it.get("meaning") or it.get("english") or it.get("back"))
        if not phrase or not meaning:
            continue
        obj = {"phrase": phrase, "meaning": meaning}
        pron = _norm_str(it.get("pronunciation") or it.get("pron"))
        if pron:
            obj["pronunciation"] = pron
        # pass through audio if provided
        au = it.get("audio_url") or it.get("audio")
        if au:
            au = _norm_str(au)
            if au.startswith("http"):
                obj["audio_url"] = au
            else:
                obj["audio"] = au
        key = (phrase.lower(), meaning.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(obj)
    return out

def normalize_passages(data: list[dict]) -> list[dict]:
    """
    Canonical for reading:
      { "polish": str, "english"?: str, "title"?: str }
    Accept synonyms: polish|phrase|front, english|meaning|back, title|name
    Deduplicates by (polish, english).
    """
    out, seen = [], set()
    for it in data or []:
        polish  = _norm_str(it.get("polish") or it.get("phrase") or it.get("front"))
        if not polish:
            continue
        obj = {"polish": polish}
        en  = _norm_str(it.get("english") or it.get("meaning") or it.get("back"))
        if en: obj["english"] = en
        title = _norm_str(it.get("title") or it.get("name"))
        if title: obj["title"] = title
        key = (polish.lower(), (obj.get("english") or "").lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(obj)
    return out

def normalize_for_modes(modes: list[str], data: list[dict]) -> list[dict]:
    """
    If the set is read-only (only 'read'), return passages; otherwise assume cards.
    """
    ms = {str(m).lower() for m in (modes or [])}
    is_read_only = (ms == {"read"}) or (list(ms) == ["read"])
    return normalize_passages(data) if is_read_only else normalize_cards(data)

# --- Azure TTS (REST) with gTTS fallback ------------------------------------
import os
def _azure_tts_enabled() -> bool:
    return bool(os.getenv("AZURE_SPEECH_KEY") and os.getenv("AZURE_SPEECH_REGION"))

def _tts_to_mp3(text: str, out_path: Path, *, voice: str | None = None) -> bool:
    """
    Try Azure Speech REST → fallback to gTTS. Returns True on success.
    Configure via env:
      AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, AZURE_TTS_VOICE (e.g., 'pl-PL-ZofiaNeural')
    """
    t = _norm_str(text)
    if not t:
        return False

    # Azure REST
    if _azure_tts_enabled():
        try:
            import requests  # type: ignore
            key    = os.getenv("AZURE_SPEECH_KEY")
            region = os.getenv("AZURE_SPEECH_REGION")
            voice  = voice or os.getenv("AZURE_TTS_VOICE", "pl-PL-ZofiaNeural")
            url    = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
            ssml   = f"<speak version='1.0' xml:lang='pl-PL'><voice xml:lang='pl-PL' xml:gender='Female' name='{voice}'>{t}</voice></speak>"
            headers = {
                "Ocp-Apim-Subscription-Key": key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-48khz-192kbitrate-mono-mp3",
                "User-Agent": "LearnPolish-Server/1.0"
            }
            r = requests.post(url, data=ssml.encode("utf-8"), headers=headers, timeout=20)
            if r.status_code == 200:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(r.content)
                return True
            else:
                print(f"⚠️ Azure TTS failed {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"⚠️ Azure TTS error: {e}")

    # gTTS fallback
    try:
        from gtts import gTTS  # type: ignore
        out_path.parent.mkdir(parents=True, exist_ok=True)
        gTTS(text=t, lang="pl").save(str(out_path))
        return True
    except Exception as e:
        print(f"⚠️ gTTS error: {e}")
        return False

# --- R2 client (safe import) -------------------------------------------------
try:
    from app.r2_client import enabled as _r2_enabled_raw, put_file as _r2_put_file
except Exception:
    _r2_enabled_raw = False
    def _r2_put_file(*_args, **_kwargs):  # type: ignore
        return None

def r2_enabled() -> bool:
    try:
        if os.getenv("DISABLE_R2") == "1":
            return False
        return bool(_r2_enabled_raw() if callable(_r2_enabled_raw) else _r2_enabled_raw)
    except Exception:
        return False


# --- Optional set_modes.json rewriter ---------------------------------------
try:
    from .create_set_modes import main as rebuild_set_modes_map
except Exception:
    def rebuild_set_modes_map():
        """Rebuild docs/set_modes.json by scanning docs/sets/*.json."""
        try:
            from .create_set_modes import main as _build
            _build()
        except Exception as e:
            print(f"⚠️ Failed to rebuild set_modes.json: {e}")

# Legacy compat: older code calls build_all_mode_indexes(); forward to set_modes rebuild.
def build_all_mode_indexes():
    try:
        rebuild_set_modes_map()
    except Exception as e:
        print(f"⚠️ build_all_mode_indexes fallback failed: {e}")

# ---------------- Utilities --------------------------------------------------

def sanitize_filename(text: str) -> str:
    """Make a safe, ASCII-only filename for storage (used for file paths)."""
    nfkd = unicodedata.normalize("NFKD", text or "")
    ascii_text = "".join([c for c in nfkd if not unicodedata.combining(c)])
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", ascii_text)
    return safe.strip("_")

def _read_json_file(p: Path) -> Optional[Any]:
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _set_file_path(set_name: str) -> Path:
    return SETS_DIR / f"{set_name}.json"

def _get_saved_modes_from_json(j: Any) -> list[str]:
    """
    Read explicit modes saved in the set JSON (no inference).
    Enforces learn<->speak pairing and canonical order.
    """
    if not isinstance(j, dict):
        return []
    modes = j.get("modes") or (j.get("meta") or {}).get("modes")
    if not isinstance(modes, list):
        return []
    allow = {"learn", "speak", "read", "listen"}
    out, seen = [], set()
    for m in modes:
        s = str(m).strip().lower()
        if s in allow and s not in seen:
            seen.add(s)
            out.append(s)
    if "learn" in seen or "speak" in seen:
        if "learn" not in seen: out.insert(0, "learn")
        if "speak" not in seen: out.insert(1, "speak")
    order = ["learn", "speak", "read", "listen"]
    return [m for m in order if m in set(out)]

def _type_from_modes(modes: list[str] | None) -> str:
    m = set(modes or [])
    if m == {"listen"}: return "listening"
    if m == {"read"}:   return "reading"
    return "flashcards"

# ---------------- Metadata / Listing ----------------------------------------

def get_set_metadata(set_name: str) -> Dict[str, Any]:
    """
    Return metadata for a single set:
      { "name", "count", "type", "created_by" }
    """
    p = _set_file_path(set_name)
    j = _read_json_file(p)
    count = 0
    modes: list[str] | None = None

    if isinstance(j, dict):
        modes = _get_saved_modes_from_json(j) or None
        if isinstance(j.get("cards"), list):      count = len(j["cards"])
        elif isinstance(j.get("passages"), list): count = len(j["passages"])
        elif isinstance(j.get("items"), list):    count = len(j["items"])
        elif isinstance(j.get("data"), list):     count = len(j["data"])  # legacy safety
    elif isinstance(j, list):
        # very old legacy: top-level array of cards
        modes = ["learn", "speak"]
        count = len(j)

    return {
        "name": set_name,
        "count": count,
        "type": _type_from_modes(modes),
        "created_by": "system",
    }

def list_global_sets() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in sorted(SETS_DIR.glob("*.json")):
        out.append(get_set_metadata(p.stem))
    return out

# ---------------- Data I/O ---------------------------------------------------

def load_set_data(set_name: str) -> Tuple[list[dict], list[str]]:
    """
    Load items for a set + return explicit modes.
    Returns: (items, modes)
    Items come from "cards" (learn/speak) OR "passages" (read) OR legacy fallbacks.
    """
    p = _set_file_path(set_name)
    j = _read_json_file(p)

    modes = []
    items: list[dict] = []

    if isinstance(j, dict):
        modes = _get_saved_modes_from_json(j)
        if (set(modes) == {"read"}) or (modes == ["read"]):
            items = j.get("passages") or []
        else:
            items = j.get("cards") or j.get("items") or j.get("data") or []
    elif isinstance(j, list):
        modes = ["learn", "speak"]
        items = j
    else:
        raise FileNotFoundError(f"Set file not found or invalid: {p}")

    if not isinstance(items, list):
        items = []
    return items, modes

def save_set_wrapper(set_name: str, modes: list[str], data: list[dict]) -> Path:
    """
    Save the canonical on-disk shape:
      - read-only → {"name","modes","meta.modes","passages":[...]}
      - else      → {"name","modes","meta.modes","cards":[...]}
    Applies normalization so callers can send forgiving keys.
    """
    safe = sanitize_filename(set_name)
    body: dict = {"name": safe, "modes": [], "meta": {"modes": []}}

    # enforce pairing + canonical order
    # accept both canonical ("learn/speak/read/listen") and page modes ("flashcards/practice/reading/listening")
    raw = {str(x).lower() for x in (modes or [])}
    page_to_canon = {
        "flashcards": "learn",
        "practice":   "speak",
        "reading":    "read",
        "listening":  "listen",
        # pass-through for canonical too
        "learn": "learn", "speak": "speak", "read": "read", "listen": "listen",
    }
    m = {page_to_canon.get(x, x) for x in raw if page_to_canon.get(x, x) in {"learn","speak","read","listen"}}

    if "learn" in m or "speak" in m:
        m.update({"learn", "speak"})
    ordered = [x for x in ["learn", "speak", "read", "listen"] if x in m]
    body["modes"] = ordered
    body["meta"]["modes"] = ordered

    # normalize data
    norm = normalize_for_modes(ordered, data or [])

    is_read_only = (set(ordered) == {"read"}) or (ordered == ["read"])
    if is_read_only:
        body["passages"] = norm
    else:
        body["cards"] = norm

    out = _set_file_path(safe)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return out

# ---------------- System audio presence -------------------------------------

def _ensure_system_audio() -> None:
    """
    Ensure the system cue directory exists and warn if any expected files are missing.
    We do NOT auto-generate these (you already have custom versions).
    """
    sys_dir = STATIC_DIR / "system_audio"
    sys_dir.mkdir(parents=True, exist_ok=True)
    missing = [n for n in SYSTEM_CUE_NAMES if not (sys_dir / f"{n}.mp3").exists()]
    if missing:
        print(f"ℹ️ System audio missing (won't auto-generate): {', '.join(missing)}")

# ---------------- Local audio generation ------------------------------------

def _ensure_flashcard_audio(set_name: str, data: List[Dict[str, Any]]) -> None:
    try:
        from gtts import gTTS
    except Exception as e:
        print(f"⚠️ gTTS not available; skipping audio generation: {e}")
        return

    audio_dir = STATIC_DIR / set_name / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    seen = set()
    for i, entry in enumerate(data):
        phrase = (entry or {}).get("phrase", "").strip()
        if not phrase or phrase in seen:
            continue
        seen.add(phrase)

        filename = f"{i}_{sanitize_filename(phrase)}.mp3"
        out = audio_dir / filename
        if out.exists():
            continue
        try:
            _tts_to_mp3(phrase, out)
        except Exception as e:
            print(f"⚠️ Failed to create TTS for '{phrase}': {e}")

def _ensure_reading_audio(set_name: str, data: List[Dict[str, Any]]) -> None:
    try:
        from gtts import gTTS
    except Exception as e:
        print(f"⚠️ gTTS not available; skipping reading audio: {e}")
        return

    audio_dir = STATIC_DIR / set_name / "reading"
    audio_dir.mkdir(parents=True, exist_ok=True)

    seen = set()
    for i, item in enumerate(data):
        polish = (item or {}).get("polish", "").strip()
        if not polish or polish in seen:
            continue
        seen.add(polish)

        out = audio_dir / f"{i}.mp3"
        if out.exists():
            continue
        try:
            _tts_to_mp3(polish, out)
        except Exception as e:
            print(f"⚠️ Failed to create reading TTS for idx {i}: {e}")

# ---------------- R2 publishing + manifest ----------------------------------

def _iter_local_assets(set_name: str):
    """
    Yield (local_path: Path, r2_key: str, ctype: str, cache_control: str)
    Keys chosen to match how front-end resolves manifest keys:
      - flashcards/practice: "audio/<set>/<file>.mp3"
      - reading:             "reading/<set>/<i>.mp3"
    """
    # flashcards/practice
    fc_dir = STATIC_DIR / set_name / "audio"
    if fc_dir.exists():
        for p in sorted(fc_dir.glob("*.mp3")):
            key = f"audio/{set_name}/{p.name}"
            yield p, key, "audio/mpeg", "public,max-age=31536000,immutable"

    # reading
    rd_dir = STATIC_DIR / set_name / "reading"
    if rd_dir.exists():
        for p in sorted(rd_dir.glob("*.mp3")):
            key = f"reading/{set_name}/{p.name}"
            yield p, key, "audio/mpeg", "public,max-age=31536000,immutable"

    # listening (if create_listening_set wrote local audio)
    ls_dir = STATIC_DIR / set_name / "listening"
    if ls_dir.exists():
        for p in sorted(ls_dir.glob("*.mp3")):
            key = f"listening/{set_name}/{p.name}"
            yield p, key, "audio/mpeg", "public,max-age=31536000,immutable"


def _write_r2_manifest(set_name: str, key_to_url: Dict[str, str]) -> Path:
    """
    Write docs/static/<set>/r2_manifest.json with structure:
      { "set": "<name>", "assetsBase": "<cdn base or ''>", "files": { "<key>": "<full CDN URL>", ... } }
    """
    out_dir = STATIC_DIR / set_name
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "set": set_name,
        "assetsBase": asset_url("").rstrip("/"),
        "files": key_to_url,
    }
    out_path = out_dir / "r2_manifest.json"
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path

def _publish_assets_to_r2(set_name: str) -> Dict[str, Any]:
    """
    Upload all local audio for a set to R2 (if configured).
    Build a manifest mapping manifest-key → full CDN URL.
    """
    if not r2_enabled():
        return {"enabled": False, "uploaded": []}

    uploaded_keys: List[str] = []
    key_to_url: Dict[str, str] = {}

    for local_path, key, ctype, cache in _iter_local_assets(set_name):
        try:
            cdn_url = _r2_put_file(
                key=key,
                body=local_path,          # Path object is OK; provider reads it
                content_type=ctype,
                cache_control=cache,
            )
            # If provider doesn't return a URL, synthesize from CDN base
            full_url = str(cdn_url) if cdn_url else asset_url(key)
            key_to_url[key] = full_url
            uploaded_keys.append(key)
        except Exception as e:
            print(f"⚠️ R2 upload failed for {local_path} → {key}: {e}")

    if key_to_url:
        man = _write_r2_manifest(set_name, key_to_url)
        print(f"☁️  R2: uploaded {len(uploaded_keys)} objects for '{set_name}'. Manifest: {man}")
    else:
        print(f"☁️  R2: no local assets to upload for '{set_name}'")

    return {"enabled": True, "uploaded": uploaded_keys}

# ---------------- Page generation -------------------------------------------

def regenerate_set_pages(set_name: str) -> bool:
    """
    Regenerate HTML + local audio based on explicit saved modes for this set.
    Generators are expected in MODE_GENERATORS with keys:
      - "flashcards" (for 'learn')
      - "practice"   (for 'speak')
      - "reading"    (for 'read')
    Listening pages/audio are handled in app/listening.py separately.
    """
    from .modes import MODE_GENERATORS  # avoid circular import

    data, modes = load_set_data(set_name)

    # Local audio first (so pages can play immediately)
    if "learn" in modes or "speak" in modes:
        _ensure_flashcard_audio(set_name, data)
    if "read" in modes:
        _ensure_reading_audio(set_name, data)

    # System cue files presence check (non-fatal)
    _ensure_system_audio()

    # Map explicit modes → generators to run
    gens = set()
    if "learn" in modes: gens.add("flashcards")
    if "speak" in modes: gens.add("practice")
    if "read"  in modes: gens.add("reading")

    for g in gens:
        gen_fn = MODE_GENERATORS.get(g)
        if gen_fn:
            html_path = gen_fn(set_name, data)
            print(f"🔄 Regenerated {g} page for set '{set_name}': {html_path}")

    # Publish local assets to R2 + write manifest (if enabled)
    _publish_assets_to_r2(set_name)

    # Keep set_modes.json fresh (cheap)
    try:
        rebuild_set_modes_map()
    except Exception as e:
        print(f"⚠️ Failed to rebuild set_modes.json: {e}")

    return True

# ---------------- High-level ops --------------------------------------------

def create_set(set_type: str, set_name: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a new set: save wrapper JSON, then generate pages/audio.
    Returns metadata for the caller.
    """
    safe_name = sanitize_filename(set_name)
    if not safe_name:
        raise ValueError("Invalid set name")

    t = (set_type or "").strip().lower()
    if t in {"flashcards", "vocab", "cards", "practice"}:
        canonical_modes = ["learn", "speak"]
    elif t in {"reading", "read"}:
        canonical_modes = ["read"]
    elif t in {"listening", "listen"}:
        canonical_modes = ["listen"]
    else:
        canonical_modes = ["learn", "speak"]

    # 1) Save canonical wrapper (cards or passages with explicit modes)
    save_set_wrapper(safe_name, canonical_modes, data or [])

    # 2) Generate static pages + audio and publish to R2 (if enabled)
    regenerate_set_pages(safe_name)

    # 3) Return metadata
    meta = get_set_metadata(safe_name)  # type/count/type
    meta["name"] = safe_name
    meta["type"] = set_type or meta.get("type") or "flashcards"
    # reflect canonical modes we just saved
    meta_modes = ["learn", "speak", "read", "listen"]
    meta["modes"] = [m for m in meta_modes if m in set(canonical_modes)]
    return meta

def delete_set_file(set_name: str) -> bool:
    """
    Delete the set JSON + generated pages + local static assets.
    Remote R2 assets are intentionally not deleted here.
    """
    safe = sanitize_filename(set_name)
    existed = False

    # Remove JSON
    p = _set_file_path(safe)
    if p.exists():
        p.unlink()
        existed = True

    # Remove static assets
    static_root = STATIC_DIR / safe
    if static_root.exists():
        for child in static_root.rglob("*"):
            try:
                child.unlink()
            except IsADirectoryError:
                pass
        for d in sorted(static_root.glob("**/*"), reverse=True):
            if d.is_dir():
                try:
                    d.rmdir()
                except OSError:
                    pass
        try:
            static_root.rmdir()
        except OSError:
            pass

    # Remove generated pages for known modes
    for mode_dir in ["flashcards", "practice", "reading", "listening"]:
        target = PAGES_DIR / mode_dir / safe
        if target.exists():
            for child in target.rglob("*"):
                try:
                    child.unlink()
                except IsADirectoryError:
                    pass
            for d in sorted(target.glob("**/*"), reverse=True):
                if d.is_dir():
                    try:
                        d.rmdir()
                    except OSError:
                        pass
            try:
                target.rmdir()
            except OSError:
                pass

    # Update set_modes.json
    try:
        rebuild_set_modes_map()
    except Exception as e:
        print(f"⚠️ Failed to rebuild set_modes.json after delete: {e}")

    return existed

# ---------------- Manifest helpers used by generators -----------------------

def load_r2_manifest(set_name: str) -> dict | None:
    p = STATIC_DIR / set_name / "r2_manifest.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None

def cdn_or_local(set_name: str, subdir: str, filename: str, r2man: dict | None):
    """
    Resolve a file path with optional R2 manifest:
      - subdir "audio"    → key "audio/<set>/<filename>"
      - subdir "reading"  → key "reading/<set>/<filename>"
    Returns absolute CDN URL if present in manifest; else local relative path used by pages:
      ../static/<set>/<subdir>/<filename>
    """
    key = f"{subdir}/{set_name}/{filename}"
    if r2man and r2man.get("files", {}).get(key):
        return r2man["files"][key]
    return f"../static/{set_name}/{subdir}/{filename}"
