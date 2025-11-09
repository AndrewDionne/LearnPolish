# app/sets_api.py
from flask import Blueprint, request, jsonify, current_app
from pathlib import Path
from shutil import rmtree
import subprocess
import os
import shlex
import json

# Optional R2 (non-blocking)
try:
    import boto3
    from botocore.client import Config as BotoConfig
except Exception:  # boto3 not installed or blocked
    boto3 = None
    BotoConfig = None

try:
    from .debug_trace import trace, _append as _trace_append
except Exception:
    def trace(f):  # no-op if tracer isn't available
        return f
    _trace_append = None

from .modes import SET_TYPES
from .models import db, UserSet
from .auth import token_required
from .sets_utils import build_all_mode_indexes


# Centralized paths + constants
from .constants import SETS_DIR, PAGES_DIR

# Canonical helpers from sets_utils
from .sets_utils import (
    sanitize_filename,
    create_set as util_create_set,
    delete_set_file,
    list_global_sets,
    get_set_metadata,
)

# Keep the map-builder explicit (no silent fallback)
from .create_set_modes import main as rebuild_set_modes_map

# Single blueprint for this module
sets_api = Blueprint("sets_api", __name__)

# Also export alias used by app factory if it imports as sets_bp
sets_bp = sets_api

# =============================================================================
# Helpers (listing / hygiene)
# =============================================================================

def _repo_has_commits(root: Path) -> bool:
    try:
        _run(["git", "rev-parse", "--verify", "HEAD"], root, check=True)
        return True
    except Exception:
        return False
    
def _git_current_commit_sha() -> str | None:
    try:
        root = Path(current_app.root_path).parent
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(root), text=True
        ).strip()
        return out or None
    except Exception:
        return None


def _global_map_by_name(global_list: list[dict]) -> dict[str, dict]:
    return {s["name"]: s for s in global_list if "name" in s}

def _with_deprecation_headers(resp, successor_path: str):
    """
    Add soft deprecation hints without breaking existing consumers.
    See: RFC 8594 (Link rel="successor-version"); Deprecation header (draft).
    """
    try:
        resp.headers["Deprecation"] = "true"
        resp.headers["Link"] = f'<{successor_path}>; rel="successor-version"'
    except Exception:
        pass
    return resp

def _apply_list_params(items: list[dict]):
    """
    Optional filters for listings:
      ?q=<substring> (case-insensitive match on name)
      ?limit=, ?offset=
      ?sort=name|count  (default=name)
      ?order=asc|desc   (default=asc)
    """
    q = (request.args.get("q") or "").strip().lower()
    sort = (request.args.get("sort") or "name").lower()
    order = (request.args.get("order") or "asc").lower()
    try:
        limit = int(request.args.get("limit", 0))
    except Exception:
        limit = 0
    try:
        offset = int(request.args.get("offset", 0))
    except Exception:
        offset = 0

    out = items
    if q:
        out = [x for x in out if q in (x.get("name") or "").lower()]

    keyfunc = (lambda x: (x.get("name") or "").lower())
    if sort == "count":
        keyfunc = (lambda x: (
            x.get("count") if isinstance(x.get("count"), int) else -1,
            (x.get("name") or "").lower()
        ))
    out.sort(key=keyfunc, reverse=(order == "desc"))

    if offset > 0 or (limit and limit > 0):
        start = max(offset, 0)
        end = start + max(limit, 0) if limit and limit > 0 else None
        out = out[start:end]

    return out

def _ensure_modes(row: dict) -> dict:
    """
    Guarantee a 'modes' array on each listing row.
    If the set JSON already has modes, keep them.
    Otherwise derive from 'type'.
    """
    try:
        if isinstance(row.get("modes"), list) and row["modes"]:
            return row
        t = (row.get("type") or "").lower()
        if t in ("flashcards", "vocab", "cards"):
            row["modes"] = ["learn", "speak"]
        elif t in ("reading", "read"):
            row["modes"] = ["read"]
        elif t in ("listening", "listen", "audio"):
            row["modes"] = ["listen"]
        else:
            row["modes"] = []
    except Exception:
        row["modes"] = []
    return row

# Replace legacy docs root alias with centralized pages dir
DOCS_ROOT = PAGES_DIR

def _safe_rmtree(p: Path):
    try:
        if p.exists():
            rmtree(p)
    except Exception:
        pass

def _delete_set_files_everywhere(set_name: str):
    # remove the JSON via existing delete_set_file (if it wraps extra logic)
    try:
        delete_set_file(set_name)
    except Exception:
        try:
            (SETS_DIR / f"{set_name}.json").unlink(missing_ok=True)
        except Exception:
            pass

    # nuke generated assets and pages
    _safe_rmtree(DOCS_ROOT / "flashcards" / set_name)
    _safe_rmtree(DOCS_ROOT / "practice"   / set_name)
    _safe_rmtree(DOCS_ROOT / "reading"    / set_name)
    _safe_rmtree(DOCS_ROOT / "listening"  / set_name)
    _safe_rmtree(DOCS_ROOT / "static"     / set_name)

# -----------------------------------------------------------------------------
# Runtime static helpers & LFS override
# -----------------------------------------------------------------------------
def _ensure_static_runtime_files() -> list[Path]:
    """
    Ensures the frontend runtime helpers exist and creates a local LFS override
    for audio so MP3s can be committed from a container without git-lfs.
    Returns a list of files that were (re)written.
    """
    created: list[Path] = []
    js_dir = PAGES_DIR / "static" / "js"
    js_dir.mkdir(parents=True, exist_ok=True)

    def _write(path: Path, content: str, *, only_if_missing: bool = False):
        if only_if_missing and path.exists():
            return
        path.write_text(content, encoding="utf-8")
        created.append(path)

    # audio-paths.js (shared resolver: R2 manifest/CDN → local)
    _write(js_dir / "audio-paths.js", r"""(function(w){
  const APP = w.APP_CONFIG || {};
  function sanitize(t){return (t||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-zA-Z0-9_-]+/g,"_").replace(/^_+|_+$/g,"");}
  async function fetchManifest(setName){
    const probes = [
      `../../static/${encodeURIComponent(setName)}/r2_manifest.json`,
      `../../static/r2_manifest.json`
    ];
    for (const u of probes){
      try{ const r = await fetch(u,{cache:"no-store"}); if(r.ok) return await r.json(); }catch(e){}
    }
    return null;
  }
  function buildAudioPath(setName, index, item, manifest){
    const fn = (item && item.audio_file) ? String(item.audio_file)
              : `${index}_${sanitize(item?.phrase||item?.polish||"")}.mp3`;
    const key = `audio/${setName}/${fn}`;
    if (manifest?.files?.[key]) return manifest.files[key];
    const base = manifest?.assetsBase || manifest?.cdn || manifest?.base || APP.assetsBase;
    if (base) return String(base).replace(/\/$/,"") + "/" + key;
    return `../../static/${encodeURIComponent(setName)}/audio/${encodeURIComponent(fn)}`;
  }
  w.AudioPaths = { fetchManifest, buildAudioPath };
})(window);
""", only_if_missing=True)

    # Legacy shim to stop 404s on older pages
    _write(js_dir / "flashcards-audio-adapter.js", "/* legacy shim: no-op */\n", only_if_missing=True)

    # Minimal config, API wrapper, and session stubs (only if missing)
    _write(js_dir / "app-config.js",
           'window.APP_CONFIG = window.APP_CONFIG || { API_BASE: "https://path-to-polish.onrender.com", assetsBase: null };\n',
           only_if_missing=True)

    _write(js_dir / "api.js", r"""window.api = {
  fetch: (path, opts={}) => {
    const base = (window.APP_CONFIG && APP_CONFIG.API_BASE) || "";
    return fetch(base.replace(/\/$/,"") + path, Object.assign({credentials:"include"}, opts));
  }
};""", only_if_missing=True)

    _write(js_dir / "session_state.js", """window.SessionSync = {
  save: async () => {}, restore: async (_k, cb)=> cb && cb(null), complete: async ()=>{}
};""", only_if_missing=True)

    # Disable Git LFS under docs/static so MP3s commit cleanly on Render
    attrs = PAGES_DIR / "static" / ".gitattributes"
    attrs.parent.mkdir(parents=True, exist_ok=True)
    if not attrs.exists():
        attrs.write_text(
            "*.mp3 -filter -diff -merge text\n*.wav -filter -diff -merge text\n",
            encoding="utf-8"
        )
        created.append(attrs)

    return created

# -----------------------------------------------------------------------------
# Optional Cloudflare R2 upload (non-blocking). Falls back to GH Pages local.
# -----------------------------------------------------------------------------
def _r2_env_ok() -> bool:
    return (
        boto3 is not None and
        os.getenv("R2_ENDPOINT") and
        os.getenv("R2_BUCKET") and
        os.getenv("R2_ACCESS_KEY") and
        os.getenv("R2_SECRET_KEY")
    )

def _r2_public_base() -> str | None:
    """
    Prefer a CDN base if you have one; else fall back to the 'public' endpoint.
    You can set R2_PUBLIC_BASE or R2_CDN_BASE to something like:
      https://assets.pathtopolish.com   (which fronts the R2 bucket)
    """
    return (os.getenv("R2_PUBLIC_BASE") or
            os.getenv("R2_CDN_BASE") or
            None)

def _try_upload_to_r2(local_path: Path, bucket_key: str) -> bool:
    try:
        if not _r2_env_ok() or not local_path.exists():
            return False
        s3 = boto3.client(
            "s3",
            endpoint_url=os.environ["R2_ENDPOINT"],
            aws_access_key_id=os.environ["R2_ACCESS_KEY"],
            aws_secret_access_key=os.environ["R2_SECRET_KEY"],
            region_name=os.getenv("R2_REGION", "auto"),
            config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "virtual"})
        )
        
        # naive content-type from extension
        ext = local_path.suffix.lower()
        ctype = "audio/mpeg" if ext == ".mp3" else ("audio/wav" if ext == ".wav" else "application/octet-stream")
        with open(local_path, "rb") as f:
            s3.put_object(
                Bucket=os.environ["R2_BUCKET"],
                Key=bucket_key,
                Body=f,
                ContentType=ctype,
                ACL="public-read",
            )
        return True
    except Exception as e:
        try:
            current_app.logger.warning("R2 upload failed for %s → %s: %s", local_path, bucket_key, e)
        except Exception:
            print(f"R2 upload failed for {local_path} → {bucket_key}: {e}")
        return False

def _maybe_upload_set_audio_to_r2(slug: str) -> Path | None:
    """
    Uploads docs/static/<slug>/audio/*.mp3 to R2 and writes a per-set manifest:
      docs/static/<slug>/r2_manifest.json
    Manifest shape: { "assetsBase": "<base or null>", "files": { "audio/<slug>/<fn>": "<absolute URL>" } }
    Returns the manifest path if written.
    """
    static_audio = PAGES_DIR / "static" / slug / "audio"
    if not static_audio.exists() or not any(static_audio.glob("*.mp3")):
        return None

    # Best-effort upload; never raise
    files_map: dict[str, str] = {}
    base = _r2_public_base()
    for mp3 in sorted(static_audio.glob("*.mp3")):
        key = f"audio/{slug}/{mp3.name}"
        ok = _try_upload_to_r2(mp3, key)
        if ok:
            if base:
                url = f"{base.rstrip('/')}/{key}"
            else:
                # If no CDN base, the S3 endpoint URL varies per account; we can still map to the 'key'
                # Frontend will use assetsBase when set; otherwise exact 'files' mapping covers it.
                # Some setups allow: https://<account-id>.r2.cloudflarestorage.com/<bucket>/<key>
                endpoint = os.getenv("R2_PUBLIC_BASE") or os.getenv("R2_ENDPOINT")
                if endpoint and endpoint.startswith("http"):
                    bucket = os.environ.get("R2_BUCKET")
                    url = f"{endpoint.rstrip('/')}/{bucket}/{key}"
                else:
                    url = key  # fallback; not great, but harmless (frontend will ignore)
            files_map[key] = url

    if not files_map:
        return None

    manifest = {
        "assetsBase": base,
        "files": files_map,
    }
    man_path = PAGES_DIR / "static" / slug / "r2_manifest.json"
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return man_path

# -----------------------------------------------------------------------------
# Audio generation (gTTS, best-effort)
# -----------------------------------------------------------------------------
def _load_cards_for_slug(slug: str) -> list[dict] | None:
    """Load cards from docs/sets JSON; returns None if read-only set."""
    path = SETS_DIR / f"{slug}.json"
    try:
        if not path.exists():
            return None
        j = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(j, dict):
            # read-only sets would have 'passages'; we only synthesize for cards
            cards = j.get("cards") or j.get("items") or j.get("data")
            return cards if isinstance(cards, list) and cards else None
        elif isinstance(j, list):
            # legacy plain list is cards
            return j
    except Exception as e:
        try: current_app.logger.warning("load_cards_for_slug(%s) failed: %s", slug, e)
        except Exception: pass
    return None

def _generate_tts_audio_for_set(slug: str, items: list[dict] | None) -> list[Path]:
    """
    Generate MP3s under docs/static/<slug>/audio/ using gTTS (Polish).
    Skips existing files. Returns list of files written.
    """
    written: list[Path] = []
    try:
        from gtts import gTTS  # type: ignore
    except Exception as e:
        try: current_app.logger.info("gTTS not available; skipping audio gen for %s (%s)", slug, e)
        except Exception: pass
        return written

    out_dir = PAGES_DIR / "static" / slug / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)

    for idx, entry in enumerate(items or []):
        try:
            phrase = str(entry.get("phrase") or "").strip()
            if not phrase:
                continue
            # mirror same filename convention used by flashcards page
            fn = f"{idx}_{sanitize_filename(phrase)}.mp3"
            dst = out_dir / fn
            if dst.exists() and dst.stat().st_size > 0:
                continue  # already there

            # synthesize
            tts = gTTS(text=phrase, lang="pl")
            tts.save(str(dst))
            written.append(dst)
        except Exception as e:
            try: current_app.logger.warning("audio gen failed [%s #%d]: %s", slug, idx, e)
            except Exception: pass

    # Best-effort: if we generated anything, return list
    if written:
        try: current_app.logger.info("audio gen wrote %d files in %s", len(written), out_dir)
        except Exception: pass
    return written


# =============================================================================
# Git publishing (Option B only: GITHUB_TOKEN + GITHUB_REPO_SLUG)
# =============================================================================

@trace
def _collect_commit_targets(slug: str, modes: list[str]) -> list[Path]:
    """
    Return a robust list of repo-relative *files and dirs* to stage.
    Includes runtime JS helpers and .gitattributes so audio commits work
    even without git-lfs inside the Render container.
    """
    targets: list[Path] = []

    # JSON
    json_path = SETS_DIR / f"{slug}.json"
    if json_path.exists():
        targets.append(json_path)

    # Per-mode pages
    for m in modes:
        d = PAGES_DIR / m / slug
        if d.exists():
            targets.append(d)
            ix = d / "index.html"
            if ix.exists():
                targets.append(ix)

    # Static assets (audio etc.) + per-set manifest
    static_dir = PAGES_DIR / "static" / slug
    if static_dir.exists():
        targets.append(static_dir)
        man = static_dir / "r2_manifest.json"
        if man.exists():
            targets.append(man)

    # Runtime JS helpers (stop 404s) + LFS override
    for p in [
        Path(".gitattributes"),  # <— root attributes FIRST CLASS citizen
        PAGES_DIR / "static" / ".gitattributes",
        PAGES_DIR / "static" / "js" / "audio-paths.js",
        PAGES_DIR / "static" / "js" / "flashcards-audio-adapter.js",
        PAGES_DIR / "static" / "js" / "app-config.js",
        PAGES_DIR / "static" / "js" / "api.js",
        PAGES_DIR / "static" / "js" / "session_state.js",
    ]:

        if p.exists():
            targets.append(p)

    # Common artifacts / indexes
    commons = [
        PAGES_DIR / "flashcards" / "index.html",
        PAGES_DIR / "practice"   / "index.html",
        PAGES_DIR / "reading"    / "index.html",
        PAGES_DIR / "listening"  / "index.html",
        PAGES_DIR / "set_modes.json",
    ]
    for p in commons:
        if p.exists():
            targets.append(p)

    return targets

def _run(cmd, cwd, check=True):
    return subprocess.run(
        cmd, cwd=str(cwd), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        check=check
    ).stdout

def _prepare_repo(root: Path, token: str, repo_slug: str, branch: str = "main") -> str:
    # Canonicalize casing for this repo to avoid "repository moved" hints
    if repo_slug.lower() == "andrewdionne/learnpolish":
        repo_slug = "AndrewDionne/LearnPolish"

   
    """Ensure identity, remote, and branch are correct for Option B."""
    # 1) identity (ok if already set)
    _run(["git", "config", "--global", "--add", "safe.directory", str(root)], root, check=False)
    _run(["git", "config", "user.name",  "Path to Polish Bot"], root, check=False)
    _run(["git", "config", "user.email", "bot@pathtopolish.app"], root, check=False)

    # 2) remote url (classic PAT over HTTPS uses owner as username)
    owner = repo_slug.split("/", 1)[0]
    remote_url = f"https://{owner}:{token}@github.com/{repo_slug}.git"
    remotes = _run(["git", "remote", "-v"], root, check=False)
    if "origin" not in remotes:
        _run(["git", "remote", "add", "origin", remote_url], root, check=True)
    else:
        _run(["git", "remote", "set-url", "origin", remote_url], root, check=False)

        # 3) branch (Render often checks out in detached HEAD or brand-new repo)
    _run(["git", "fetch", "origin", "--prune"], root, check=False)

    # Detect if repository has no commits (unborn HEAD)
    unborn = False
    try:
        _run(["git", "rev-parse", "--verify", "HEAD"], root, check=True)
    except Exception:
        unborn = True

    # Check if the target branch exists on the remote
    has_remote_branch = False
    try:
        _run(["git", "rev-parse", "--verify", f"origin/{branch}"], root, check=True)
        has_remote_branch = True
    except Exception:
        pass

    if unborn:
        if has_remote_branch:
            # Start local branch from remote tip
            _run(["git", "checkout", "-B", branch, f"origin/{branch}"], root, check=True)
            unborn = False
        else:
            # Create an orphan branch so we can make the first commit
            try:
                _run(["git", "switch", "--orphan", branch], root, check=True)
            except Exception:
                _run(["git", "checkout", "--orphan", branch], root, check=True)
    else:
        current = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], root, check=False).strip()
        if current == "HEAD":
            # Detached HEAD → reattach to target branch (create if needed)
            try:
                _run(["git", "checkout", branch], root, check=True)
            except Exception:
                _run(["git", "checkout", "-B", branch], root, check=True)
        else:
            # Already on a branch; switch/create target branch as needed
            try:
                _run(["git", "checkout", branch], root, check=True)
            except Exception:
                _run(["git", "checkout", "-B", branch], root, check=True)

    # Best-effort: set upstream (ignore if remote branch doesn't exist yet)
    _run(["git", "branch", "--set-upstream-to", f"origin/{branch}", branch], root, check=False)

    # If we still have no commits (fresh orphan), seed an empty commit so pushes work
    still_unborn = False
    try:
        _run(["git", "rev-parse", "--verify", "HEAD"], root, check=True)
    except Exception:
        still_unborn = True
    if still_unborn:
        _run(["git", "commit", "--allow-empty", "-m", "chore: initial branch"], root, check=False)

    # Optional fast-forward; harmless if branch is new or remote has no tip
    _run(["git", "pull", "--ff-only", "origin", branch], root, check=False)

    return remote_url

@trace
def _git_add_commit_push(paths: list[Path], message: str) -> None:
    """
    Add/commit/push repo-relative paths to GitHub using ONLY:
      - GITHUB_TOKEN
      - GITHUB_REPO_SLUG (e.g. "AndrewDionne/LearnPolish")
      - GIT_BRANCH (default: "main")
    Staging is hardened to avoid pathspec failures when some paths are created just-in-time.
    """
    root = Path(current_app.root_path).parent  # repo root on Render

    def log_i(msg: str):
        print(msg, flush=True)
        try:
            current_app.logger.info(msg)
        except Exception:
            pass

    def run(args: list[str], ok_if_fails: bool = False) -> str:
        cmd = " ".join(args)
        log_i(f"git$ {cmd}")
        try:
            out = subprocess.check_output(
                args, cwd=str(root), stderr=subprocess.STDOUT, text=True
            )
            if out.strip():
                log_i(out.strip())
            if _trace_append:
                _trace_append("git", {"cmd": args, "ok": True, "out": out.strip()[:2000]})
            return out
        except subprocess.CalledProcessError as e:
            msg = (e.output or "").strip()
            log_i(f"❌ git error:\n{msg}")
            if _trace_append:
                _trace_append("git", {"cmd": args, "ok": False, "out": msg[:2000]})
            if ok_if_fails:
                return msg
            raise

    # ------------------------
    # Env (Option B only)
    # ------------------------
    token     = os.getenv("GITHUB_TOKEN")
    repo_slug = os.getenv("GITHUB_REPO_SLUG") or os.getenv("GITHUB_REPOSITORY")
    branch    = (os.getenv("GIT_BRANCH") or "main").strip() or "main"
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set (Option B)")
    if not repo_slug:
        raise RuntimeError("GITHUB_REPO_SLUG (or GITHUB_REPOSITORY) is not set (Option B)")

    # Ensure repo/init
    if not (root / ".git").exists():
        run(["git", "init"])

    # Prepare remote + branch (handles identity, detached HEAD, upstream)
    _prepare_repo(root, token, repo_slug, branch)

    # Normalize to repo-relative paths (robust even if inputs are relative)
    to_add_rel: list[str] = []
    for p in paths:
        if not p:
            continue
        p = Path(p)
        p_abs = p if p.is_absolute() else (root / p)
        if not p_abs.exists():
            continue
        rel = p_abs.relative_to(root)
        to_add_rel.append(str(rel))

    if not to_add_rel:
        raise RuntimeError("Nothing to push (no repo-relative files)")

    # ------------------------------------------------------------------
    # Stage aggressively; on failure, fall back to per-path + docs scope
    # ------------------------------------------------------------------
  
    # Ensure attributes are staged before any binaries to avoid CRLF warnings
    attrs_first = [p for p in (".gitattributes", "docs/static/.gitattributes") if p in to_add_rel]
    if attrs_first:
        to_add_rel = attrs_first + [p for p in to_add_rel if p not in attrs_first]

    try:
        run(["git", "add", "-A", "--"] + to_add_rel)
    except subprocess.CalledProcessError:
        log_i("git add failed on combined pathspec; falling back to per-path adds")
        for rel in to_add_rel:
            # normal add (ok if ignored)
            run(["git", "add", "-A", "--", rel], ok_if_fails=True)
            # force-add in case .gitignore matches
            run(["git", "add", "-f", "--", rel], ok_if_fails=True)
        # Stage the entire 'docs' subtree as a scoped safety net
        run(["git", "add", "-A", "--", "docs"], ok_if_fails=True)
        # and force-add docs as a last resort
        run(["git", "add", "-f", "--", "docs"], ok_if_fails=True)

    # Commit (allow empty so we always have a branch tip)
    run(["git", "commit", "-m", message, "--no-gpg-sign"], ok_if_fails=True)

    # Push (retry once after rebase)
    try:
        run(["git", "push", "origin", f"HEAD:{branch}"])
    except subprocess.CalledProcessError:
        log_i("git push rejected; pulling --rebase and retrying")
        run(["git", "pull", "--rebase", "origin", branch], ok_if_fails=True)
        run(["git", "push", "origin", f"HEAD:{branch}"])

@trace
def _push_and_verify(slug: str, gen_modes: list[str], primary_message: str) -> None:
    """
    Primary push via _git_add_commit_push(); if Git still reports changes for
    this slug, run a conservative fallback that adds specific paths again.
    """
    # Primary pass
    targets = _collect_commit_targets(slug, gen_modes)
    current_app.logger.info("publish targets for %s -> %s", slug, [str(t) for t in targets])
    _git_add_commit_push(targets, primary_message)

    # Verify working tree is clean for this slug
    root = Path(current_app.root_path).parent
    try:
        # Only check the paths we actually track for this slug
        check_paths = [
            str(SETS_DIR / f"{slug}.json"),
            str(PAGES_DIR / "flashcards" / slug),
            str(PAGES_DIR / "practice"   / slug),
            str(PAGES_DIR / "reading"    / slug),
            str(PAGES_DIR / "listening"  / slug),
            str(PAGES_DIR / "static"     / slug),
        ]

        out = subprocess.check_output(
            ["git", "status", "--porcelain", "--"] + check_paths,
            cwd=str(root), stderr=subprocess.STDOUT, text=True
        )
    except subprocess.CalledProcessError as e:
        out = e.output

    if not (out or "").strip():
        return  # clean for this slug; nothing else to do

    current_app.logger.warning(
        "post-push verify: still see changes for %s; running fallback add/commit/push",
        slug
    )

    # Conservative, file-focused fallback
    specific: list[Path] = []
    json_path = SETS_DIR / f"{slug}.json"
    if json_path.exists():
        specific.append(json_path)

    for m in gen_modes:
        d = PAGES_DIR / m / slug
        if d.exists():
            specific.append(d)
            ix = d / "index.html"
            if ix.exists():
                specific.append(ix)

    static_dir = PAGES_DIR / "static" / slug
    if static_dir.exists():
        specific.append(static_dir)

    # Re-add common indexes (harmless if unchanged)
    for p in [
        PAGES_DIR / "flashcards" / "index.html",
        PAGES_DIR / "practice"   / "index.html",
        PAGES_DIR / "reading"    / "index.html",
        PAGES_DIR / "listening"  / "index.html",
        PAGES_DIR / "set_modes.json",
    ]:
        if p.exists():
            specific.append(p)

    _git_add_commit_push(specific, f"{primary_message} (verify-fix)")

# =============================================================================
# Page regeneration
# =============================================================================
@trace
def _regen_pages_for_slug(slug: str, modes: list[str]) -> None:
    """
    Rebuild pages for this slug, adapting to whichever generator signature exists.
    Prefers sets_utils.regenerate_set_pages; falls back to per-mode modules.
    """
    from . import sets_utils

    regen = getattr(sets_utils, "regenerate_set_pages", None)
    if regen:
        try:
            regen(slug, modes=modes, force=True, verbose=True); return
        except TypeError:
            pass
        try:
            regen(slug, force=True, verbose=True); return
        except TypeError:
            pass
        try:
            regen(slug, force=True); return
        except TypeError:
            pass
        regen(slug); return

    def _try_module(mod_name, funcs):
        try:
            mod = __import__(f"app.{mod_name}", fromlist=["*"])
        except Exception:
            return False
        for fn in funcs:
            f = getattr(mod, fn, None)
            if not f:
                continue
            try:
                f(slug); return True
            except TypeError:
                try:
                    f(slug, force=True); return True
                except Exception:
                    continue
        return False

    for m in modes:
        if m == "flashcards":
            _try_module("flashcards", ["generate_set_pages", "generate_pages", "build_pages"])
        elif m == "practice":
            _try_module("practice",   ["generate_set_pages", "generate_pages", "build_pages"])
        elif m == "reading":
            _try_module("reading",    ["generate_set_pages", "generate_pages", "build_pages"])
        elif m == "listening":
            _try_module("listening",  ["create_listening_set", "generate_set_pages", "generate_pages", "build_pages"])

    # Post-check: log missing expectations (non-fatal)
    expected = []
    if "flashcards" in modes: expected.append(PAGES_DIR / "flashcards" / slug / "index.html")
    if "practice"   in modes: expected.append(PAGES_DIR / "practice"   / slug / "index.html")
    if "reading"    in modes: expected.append(PAGES_DIR / "reading"    / slug / "index.html")
    if "listening"  in modes: expected.append(PAGES_DIR / "listening"  / slug / "index.html")
    missing = [p for p in expected if not p.exists()]
    if missing:
        current_app.logger.warning("create_set_v2: expected pages missing for %s -> %s",
                                   slug, [str(p) for p in missing])

# =============================================================================
# API (NOTE: Blueprint is mounted at url_prefix="/api" in app factory)
# =============================================================================

# 0) Global sets (canonical shape)
@sets_api.route("/global_sets", methods=["GET"])
def global_sets():
    """
    Returns: [
      { "name": "...", "count": 123, "type": "flashcards|reading|unknown", "created_by": "system|user|me" },
      ...
    ]
    Optional filters: ?q=&limit=&offset=&sort=name|count&order=asc|desc
    """
    glist = list_global_sets()
    glist = _apply_list_params(glist)
    glist = [_ensure_modes(x) for x in glist]
    resp = jsonify(glist)
    return _with_deprecation_headers(resp, "/api/sets/available")

# 1) My sets (canonical shape, mark ownership and enrich private)
@sets_api.route("/my_sets", methods=["GET"])
@token_required
def my_sets(current_user):
    """
    Returns the SAME canonical shape as global_sets, for the current user's library.
    Ownership (for showing the 🗑️ Delete button):
      - If UserSet.is_owner == True -> created_by = "me"
      - Else if present in global -> keep global's created_by (usually "system")
      - Else (not in global) -> treat as private -> created_by = "me"
    """
    rows = UserSet.query.filter_by(user_id=current_user.id).all()
    user_names = [r.set_name for r in rows]
    ownership = {r.set_name: bool(getattr(r, "is_owner", False)) for r in rows}

    glist = list_global_sets()
    gmap = _global_map_by_name(glist)

    out = []
    for name in sorted(set(user_names)):
        if name in gmap:
            meta = gmap[name].copy()
            if ownership.get(name):
                meta["created_by"] = "me"
            meta = _ensure_modes(meta)
            out.append(meta)
        else:
            meta = get_set_metadata(name)
            meta["created_by"] = "me"
            meta = _ensure_modes(meta)
            out.append(meta)

    out = _apply_list_params(out)
    resp = jsonify(out)
    return _with_deprecation_headers(resp, "/api/my/sets")

# 2) Add a set to user library
@sets_api.route("/add_set", methods=["POST"])
@token_required
def add_set(current_user):
    data = request.get_json(silent=True) or {}
    set_name = (data.get("set_name") or "").strip()
    if not set_name:
        return jsonify({"message": "Set name required"}), 400

    set_name = sanitize_filename(set_name)
    existing = UserSet.query.filter_by(user_id=current_user.id, set_name=set_name).first()
    if existing:
        resp = jsonify({"message": "Already in your collection"})
        return _with_deprecation_headers(resp, "/api/my/sets")

    db.session.add(UserSet(user_id=current_user.id, set_name=set_name, is_owner=False))
    db.session.commit()
    resp = jsonify({"message": f"Set '{set_name}' added to your collection"})
    return _with_deprecation_headers(resp, "/api/my/sets")

# 3) Remove a set from user library
@sets_api.route("/remove_set", methods=["POST"])
@token_required
def remove_set(current_user):
    data = request.get_json(silent=True) or {}
    set_name = (data.get("set_name") or "").strip()
    if not set_name:
        return jsonify({"message": "Set name required"}), 400

    set_name = sanitize_filename(set_name)
    user_set = UserSet.query.filter_by(user_id=current_user.id, set_name=set_name).first()
    if not user_set:
        resp = jsonify({"message": "Set not in your collection"})
        return _with_deprecation_headers(resp, f"/api/my/sets/{set_name}")

    db.session.delete(user_set)
    db.session.commit()
    resp = jsonify({"message": f"Set '{set_name}' removed from your collection"})
    return _with_deprecation_headers(resp, f"/api/my/sets/{set_name}")

# 4) Create a set (owner-only on create)
@sets_api.route("/create_set_v2", methods=["POST"])
@token_required
@trace
def create_set(current_user):
    current_app.logger.info("create_set_v2: start")

    body = request.get_json(silent=True) or {}
    set_type = (body.get("set_type") or "").strip().lower()
    set_name = (body.get("set_name") or "").strip()
    items = body.get("data")

    # ---- validation ----
    if set_type not in SET_TYPES:
        return jsonify({"message": f"Invalid set_type. Allowed: {sorted(SET_TYPES)}"}), 400
    if not set_name:
        return jsonify({"message": "set_name is required"}), 400
    if not isinstance(items, list) or not items:
        return jsonify({"message": "data must be a non-empty JSON array"}), 400

    safe_name = sanitize_filename(set_name)
    if not safe_name:
        return jsonify({"message": "Invalid set_name"}), 400

    json_path = SETS_DIR / f"{safe_name}.json"

    # Ensure runtime helpers exist (and git-lfs override) before any publish
    _ensure_static_runtime_files()


    # generation modes (internal generator names)
    implied = {
        "flashcards": ["flashcards", "practice"],
        "reading":    ["reading"],
        "listening":  ["listening"],
        "practice":   ["practice"],
    }
    gen_modes = implied.get(set_type, ["flashcards", "practice"])

    # map generator names -> client names
    CLIENT_MODE = {
        "flashcards": "learn",
        "practice":   "speak",
        "reading":    "read",
        "listening":  "listen",
    }

    def _augment_meta(meta: dict | None, *, existed: bool) -> dict:
        """
        Normalize the response so the client always sees:
          - set_name, slug
          - modes: ["learn","speak",...]
          - pages: {"learn": "/flashcards/<slug>/", ...}
        """
        meta = dict(meta or {})
        meta.setdefault("set_name", set_name)
        meta.setdefault("slug", safe_name)
        meta["modes"] = [CLIENT_MODE[m] for m in gen_modes if m in CLIENT_MODE]
        meta["pages"] = {CLIENT_MODE[m]: f"/{m}/{safe_name}/" for m in gen_modes if m in CLIENT_MODE}
        if existed:
            meta["note"] = "already_existed_regenerated"
        return meta

    existed = json_path.exists()

    try:
        # ---------- IDEMPOTENT REBUILD ----------
        if existed:
            _regen_pages_for_slug(safe_name, gen_modes)

            # Generate / refresh audio (best-effort) from current JSON on disk
            try:
                _items = _load_cards_for_slug(safe_name)
                if _items:
                    _generate_tts_audio_for_set(safe_name, _items)
            except Exception as _e:
                current_app.logger.warning("audio gen skipped/failed for %s: %s", safe_name, _e)

            # Optional: attempt R2 upload for audio (never blocks)
            try:
                _maybe_upload_set_audio_to_r2(safe_name)

            except Exception as _e:
                current_app.logger.warning("R2 upload skipped/failed for %s: %s", safe_name, _e)

            
            # best-effort index rebuilds
            try:
                build_all_mode_indexes()
            except Exception as e:
                current_app.logger.warning("Failed to rebuild mode indexes: %s", e)
            try:
                rebuild_set_modes_map()
            except Exception as e:
                current_app.logger.warning("Failed to rebuild set_modes.json after create: %s", e)

            _push_and_verify(safe_name, gen_modes, f"rebuild: {safe_name} [{','.join(gen_modes)}]")

            sha = _git_current_commit_sha()
            meta = get_set_metadata(safe_name)
            out = _augment_meta(meta, existed=True)
            if sha:
                out["deploy"] = {
                    "commit": sha,
                    "status_href": f"/api/pages/status?commit={sha}"
                }
            resp = jsonify(out)
            resp.headers["X-Create-Handler"] = "v2"
            return resp, 200

        # ---------- NEW CREATE ----------
        meta = util_create_set(set_type, safe_name, items)

        # link user as owner (idempotent)
        link = UserSet.query.filter_by(user_id=current_user.id, set_name=safe_name).first()
        if not link:
            db.session.add(UserSet(user_id=current_user.id, set_name=safe_name, is_owner=True))
        else:
            link.is_owner = True
        db.session.commit()

        # generate static pages
        _regen_pages_for_slug(safe_name, gen_modes)

        # Generate audio for cards (best-effort)
        try:
            _generate_tts_audio_for_set(safe_name, items)
        except Exception as _e:
            current_app.logger.warning("audio gen skipped/failed for %s: %s", safe_name, _e)

        # Optional: attempt R2 upload for audio (never blocks)
        try:
            _maybe_upload_set_audio_to_r2(safe_name)

        except Exception as _e:
            current_app.logger.warning("R2 upload skipped/failed for %s: %s", safe_name, _e)

        # best-effort index rebuilds
        try:
            build_all_mode_indexes()
        except Exception as e:
            current_app.logger.warning("Failed to rebuild mode indexes: %s", e)
        try:
            rebuild_set_modes_map()
        except Exception as e:
            current_app.logger.warning("Failed to rebuild set_modes.json after create: %s", e)

        # push to GitHub (with verification)
        _push_and_verify(safe_name, gen_modes, f"build: {safe_name} [{','.join(gen_modes)}]")

        sha = _git_current_commit_sha()
        out = _augment_meta(meta, existed=False)
        out["created_by"] = "me"
        if sha:
            out["deploy"] = {
                "commit": sha,
                "status_href": f"/api/pages/status?commit={sha}"
            }
        resp = jsonify(out)
        resp.headers["X-Create-Handler"] = "v2"
        return resp, 201


    except Exception as e:
        current_app.logger.exception("create_set_v2 failed for %s: %s", safe_name, e)
        return jsonify({"message": "Failed to create set", "error": str(e)}), 500

# 5) Delete a set (owner-only)
@sets_api.route("/delete_set/<string:set_name>", methods=["POST"])
@token_required
def delete_set(current_user, set_name):
    """
    Owner action:
      - If only the owner has this set: delete files and unlink all rows.
      - If others also have it: transfer ownership to another user, unlink current owner, keep files.
    """
    safe_name = sanitize_filename(set_name or "")
    if not safe_name:
        return jsonify({"message": "Invalid set name"}), 400

    links = UserSet.query.filter_by(set_name=safe_name).all()
    if not links:
        try:
            _delete_set_files_everywhere(safe_name)
        except Exception:
            pass
        return jsonify({"ok": True, "deleted": True}), 200

    me_link = next((l for l in links if l.user_id == current_user.id), None)
    if not me_link or not getattr(me_link, "is_owner", False):
        return jsonify({"message": "Only the owner can delete this set"}), 403

    others = [l for l in links if l.user_id != current_user.id]

    if not others:
        for l in links:
            db.session.delete(l)
        db.session.commit()
        try:
            _delete_set_files_everywhere(safe_name)
        except Exception:
            pass
        try:
            build_all_mode_indexes()
        except Exception as e:
            current_app.logger.warning("Failed to rebuild mode indexes after delete: %s", e)
        try:
            rebuild_set_modes_map()
        except Exception as e:
            current_app.logger.warning("Failed to rebuild set_modes.json after delete: %s", e)
        return jsonify({"ok": True, "deleted": True}), 200

    new_owner_link = sorted(others, key=lambda l: l.id)[0]
    me_link.is_owner = False
    new_owner_link.is_owner = True
    db.session.delete(me_link)
    db.session.commit()

    try:
        build_all_mode_indexes()
    except Exception as e:
        current_app.logger.warning("Failed to rebuild mode indexes after handover: %s", e)
    try:
        rebuild_set_modes_map()
    except Exception as e:
        current_app.logger.warning("Failed to rebuild set_modes.json after handover: %s", e)

    return jsonify({"ok": True, "handover": True, "new_owner_id": new_owner_link.user_id}), 200

# 6) Admin build & publish (server-side)
@sets_api.route("/admin/build_publish", methods=["POST", "OPTIONS"])
@token_required
@trace
def admin_build_publish(current_user):
    """
    Admin-only: rebuild static pages for a slug and push to GitHub.
    Body: { "slug": "10LS", "modes": ["flashcards","reading","listening","practice"]? }
    """
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    slug = sanitize_filename((body.get("slug") or "").strip())
    modes = body.get("modes") or ["flashcards", "practice"]

    if not slug:
        return jsonify({"ok": False, "error": "slug required"}), 400

    # Ensure runtime helpers & LFS override exist for admin builds
    _ensure_static_runtime_files()

    json_path = SETS_DIR / f"{slug}.json"
    if not json_path.exists():
        current_app.logger.warning("Set JSON not found at %s; generator may still handle DB-based sets.", json_path)

    try:
        _regen_pages_for_slug(slug, modes)
        # Try R2 upload (never blocks)
        try:
            _maybe_upload_set_audio_to_r2(slug)
        except Exception as _e:
            current_app.logger.warning("R2 upload skipped/failed for %s: %s", slug, _e)

        try:
            build_all_mode_indexes()
        except Exception as e:
            current_app.logger.warning("Failed to rebuild mode indexes: %s", e)
        try:
            rebuild_set_modes_map()
        except Exception as e:
            current_app.logger.warning("Failed to rebuild set_modes.json: %s", e)

        # Log what we think changed (non-authoritative; push verifies)
        changed: list[Path] = []
        if json_path.exists():
            changed.append(json_path)
        for m in modes:
            p = PAGES_DIR / m / slug
            if p.exists():
                changed.append(p)
        for p in [
            PAGES_DIR / "flashcards" / "index.html",
            PAGES_DIR / "practice"   / "index.html",
            PAGES_DIR / "reading"    / "index.html",
            PAGES_DIR / "listening"  / "index.html",
            PAGES_DIR / "set_modes.json",
        ]:
            if p.exists():
                changed.append(p)
        current_app.logger.info("admin_build_publish: will push %s", [str(x) for x in changed])

        _push_and_verify(slug, modes, f"build: {slug} [{','.join(modes)}]")

        return jsonify({"ok": True}), 200

    except Exception as e:
        current_app.logger.exception("admin_build_publish failed for %s", slug)
        return jsonify({"ok": False, "error": str(e)}), 500

@sets_api.route("/admin/git_diag", methods=["GET"])
@token_required
def admin_git_diag(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    root = Path(current_app.root_path).parent

    def run(cmd: str):
        try:
            out = subprocess.check_output(shlex.split(cmd), cwd=str(root))
            return out.decode("utf-8", "ignore").strip()
        except Exception as e:
            return f"ERROR: {e!r}"

    def redact(url: str) -> str:
        if not isinstance(url, str):
            return url
        val = url
        for k in ("GITHUB_TOKEN", "GH_TOKEN"):
            tok = os.getenv(k, "")
            if tok:
                val = val.replace(tok, "****")
        return val

    data = {
        "cwd": str(root),
        "exists": {
            "has_dot_git": (root / ".git").exists(),
            "sets_dir": SETS_DIR.exists(),
            "pages_dir": PAGES_DIR.exists(),
        },
        "git": {
            "inside_work_tree": run("git rev-parse --is-inside-work-tree"),
            "branch":           run("git rev-parse --abbrev-ref HEAD"),
            "status":           run("git status --porcelain"),
            "remotes":          redact(run("git remote -v")),
            "last_commit":      run("git log -1 --oneline"),
            "config_user_name": run("git config user.name"),
            "config_user_email":run("git config user.email"),
        },
        "env": {
            "GIT_BRANCH": os.getenv("GIT_BRANCH"),
            "GIT_REMOTE": redact(os.getenv("GIT_REMOTE") or ""),
            "GITHUB_REPO_SLUG": os.getenv("GITHUB_REPO_SLUG"),
            "GITHUB_REPOSITORY": os.getenv("GITHUB_REPOSITORY"),
            "HAS_GITHUB_TOKEN": bool(os.getenv("GITHUB_TOKEN")),
            "HAS_GH_TOKEN": bool(os.getenv("GH_TOKEN")),
        },
        "paths": {
            "repo_root": str(root),
            "SETS_DIR": str(SETS_DIR),
            "PAGES_DIR": str(PAGES_DIR),
        }
    }
    return jsonify({"ok": True, **data}), 200

@sets_api.route("/admin/audio_diag", methods=["GET"])
@token_required
def admin_audio_diag(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    slug = sanitize_filename((request.args.get("slug") or "").strip())
    if not slug:
        return jsonify({"ok": False, "error": "slug required"}), 400

    static_dir = PAGES_DIR / "static" / slug / "audio"
    files = []
    if static_dir.exists():
        files = [p.name for p in sorted(static_dir.glob("*.mp3"))]
    exists = len(files) > 0

    manifest = (PAGES_DIR / "static" / slug / "r2_manifest.json")
    man_exists = manifest.exists()
    man_size = manifest.stat().st_size if man_exists else 0

    return jsonify({
        "ok": True,
        "slug": slug,
        "audio_dir": str(static_dir),
        "count": len(files),
        "files": files[:20],  # sample
        "has_manifest": man_exists,
        "manifest_size": man_size,
    })


@sets_api.route("/pages/status", methods=["GET"])
@token_required
def pages_status(current_user):
    """
    Check GitHub Pages build/deploy status.
    Query params:
      - commit (optional): if provided, returns deployed:=true iff latest build is 'built' AND commit matches.
    """
    import requests

    token  = os.getenv("GITHUB_TOKEN")
    slug   = os.getenv("GITHUB_REPO_SLUG") or os.getenv("GITHUB_REPOSITORY")
    want   = (request.args.get("commit") or "").strip()

    if not token or not slug:
        return jsonify({"ok": False, "error": "missing_github_env"}), 500

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "PathToPolish-App",
    }

    def _get_json(url: str):
        try:
            r = requests.get(url, headers=headers, timeout=10)
            return r.status_code, (r.json() if r.content else {})
        except Exception as e:
            return 599, {"error": str(e)}

    # latest build
    sc, latest = _get_json(f"https://api.github.com/repos/{slug}/pages/builds/latest")
    if sc // 100 != 2:
        return jsonify({"ok": False, "where": "builds/latest", "status": sc, "detail": latest}), 502

    # site info (to compute the public base URL)
    sc2, site = _get_json(f"https://api.github.com/repos/{slug}/pages")

    # Compute a best-effort public base
    base = None
    if sc2 // 100 == 2:
        base = site.get("html_url") or (("https://" + site.get("domain")) if site.get("domain") else None)

    # Fallback to common project-pages pattern if needed
    if not base:
        owner = slug.split("/")[0]
        repo  = slug.split("/")[1]
        base  = f"https://{owner}.github.io/{repo}"

    status  = (latest.get("status") or "").lower()  # queued | building | built | errored
    lcommit = latest.get("commit") or ""
    deployed = (status == "built" and (not want or want == lcommit))

    out = {
        "ok": True,
        "status": status,
        "latest_commit": lcommit or None,
        "deployed": deployed,
        "pages_base": base,
        "build": {
            "created_at": latest.get("created_at"),
            "updated_at": latest.get("updated_at"),
            "error": (latest.get("error") or {}).get("message"),
            "duration": latest.get("duration"),
        },
        "site": {
            "cname": site.get("cname") if isinstance(site, dict) else None,
            "source": (site.get("source") or {}) if isinstance(site, dict) else {},
        }
    }
    return jsonify(out), 200


@sets_api.route("/admin/publish_now", methods=["POST"])
@token_required
@trace
def admin_publish_now(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    slug  = sanitize_filename((body.get("slug") or "").strip())
    modes = body.get("modes") or ["flashcards","practice"]
    if not slug:
        return jsonify({"ok": False, "error": "slug required"}), 400
    # Ensure runtime helpers & LFS override exist for admin “publish now”
    _ensure_static_runtime_files()

    # Always regenerate before pushing
    try:
        _regen_pages_for_slug(slug, modes)
        # Try R2 upload (never blocks)
        try:
            _maybe_upload_set_audio_to_r2(slug)
        except Exception as _e:
            current_app.logger.warning("R2 upload skipped/failed for %s: %s", slug, _e)

    except Exception as e:
        current_app.logger.warning("publish_now: regen failed: %s", e)

    targets = _collect_commit_targets(slug, modes)
    _git_add_commit_push(targets, f"manual: {slug} [{','.join(modes)}]")

    # Return a short summary + current git status
    root = Path(current_app.root_path).parent
    try:
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=str(root), text=True)
    except subprocess.CalledProcessError as e:
        status = e.output
    try:
        rem = subprocess.check_output(["git", "remote", "-v"], cwd=str(root), text=True)
    except subprocess.CalledProcessError as e:
        rem = e.output

    return jsonify({
        "ok": True,
        "slug": slug,
        "modes": modes,
        "pushed": [str(p) for p in targets],
        "git_status": status,
        "git_remotes": rem
    }), 200

@sets_api.route("/admin/push", methods=["POST"])
@token_required
@trace
def admin_push(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    # Ensure runtime helpers exist in case this push is used standalone
    _ensure_static_runtime_files()
    slug = sanitize_filename((body.get("slug") or "").strip())
    modes = body.get("modes") or ["flashcards", "practice"]

    if not slug:
        return jsonify({"ok": False, "error": "slug required"}), 400

    targets = _collect_commit_targets(slug, modes)
    _git_add_commit_push(targets, f"manual: {slug} [{','.join(modes)}]")

    # quick verify summary
    root = Path(current_app.root_path).parent
    out = subprocess.check_output(["git", "status", "--porcelain"], cwd=str(root), text=True)
    return jsonify({"ok": True, "pushed": [str(p) for p in targets], "status": out}), 200

@sets_api.route("/admin/git_smoke", methods=["POST"], endpoint="sets_admin_git_smoke")
@token_required
@trace
def admin_git_smoke(current_user):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "forbidden"}), 403
    try:
        from datetime import datetime, timezone
        slug = ".publish_smoke"
        marker = PAGES_DIR / slug  # e.g., docs/.publish_smoke
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(f"ok {datetime.now(timezone.utc).isoformat()}\n", encoding="utf-8")

        _git_add_commit_push([marker], "chore: publish smoke marker")
        return jsonify({"ok": True, "path": str(marker)}), 200
    except Exception as e:
        # always JSON on error
        return jsonify({"ok": False, "error": str(e)}), 500
