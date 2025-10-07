# app/git_utils.py
import os
import shutil
from pathlib import Path
from typing import Iterable, List, Optional

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError

# === Constants ===
REPO_PATH = Path(__file__).resolve().parent.parent
GIT_DIR = REPO_PATH / ".git"
LOCK_FILE = GIT_DIR / "index.lock"
PUSH_LOCK = REPO_PATH / ".push_in_progress"

# Keep in sync with app/modes.py AVAILABLE_MODES if you want,
# but for deletion it's fine to cover the known folders:
MODES = ["flashcards", "practice", "reading", "listening", "test"]


# ---------------------------
# Internal helpers
# ---------------------------

def _safe_remove(p: Path) -> bool:
    """Remove a file or directory tree if it exists. Return True if something was removed."""
    try:
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
            print(f"🧹 Deleted directory: {p}")
            return True
        if p.is_file():
            p.unlink(missing_ok=True)
            print(f"🧹 Deleted file: {p}")
            return True
        return False
    except Exception as e:
        print(f"⚠️ Failed to delete {p}: {e}")
        return False


def _set_paths_for_delete(set_name: str) -> List[Path]:
    """
    All paths we want to remove for a set:
      - docs/sets/<set>.json
      - docs/static/<set>/...
      - docs/<mode>/<set>/...
      - (legacy) docs/output/<set>/...
    """
    paths: List[Path] = [
        REPO_PATH / "docs" / "sets" / f"{set_name}.json",
        REPO_PATH / "docs" / "static" / set_name,
        REPO_PATH / "docs" / "output" / set_name,  # legacy
    ]
    for mode in MODES:
        paths.append(REPO_PATH / "docs" / mode / set_name)
    return paths


def _repo_or_none() -> Optional[Repo]:
    try:
        return Repo(REPO_PATH)
    except (InvalidGitRepositoryError, NoSuchPathError):
        print(f"ℹ️ Not a Git repository at {REPO_PATH} (skipping commit/push).")
        return None


def _git_config(repo: Repo) -> None:
    """Set identity + safe.directory to avoid 'dubious ownership'."""
    try:
        name = os.getenv("GIT_AUTHOR_NAME", "Render Bot")
        email = os.getenv("GIT_AUTHOR_EMAIL", "bot@example.com")
        repo.git.config("user.name", name)
        repo.git.config("user.email", email)
        # Mark the checkout as safe (Render uses a system user)
        repo.git.config("--global", "safe.directory", str(REPO_PATH))
    except Exception as e:
        print(f"⚠️ git config failed: {e}")


def _ensure_branch(repo: Repo) -> str:
    """Checkout the desired branch; handle detached HEAD."""
    desired = os.getenv("GIT_BRANCH", "main")
    try:
        try:
            current = repo.active_branch.name
        except Exception:
            current = None  # detached HEAD

        if current == desired:
            return desired

        if desired in [h.name for h in repo.heads]:
            repo.git.checkout(desired)
        else:
            # Create or reset branch at current HEAD
            repo.git.checkout("-B", desired)
        return desired
    except Exception as e:
        print(f"⚠️ could not switch to branch {desired}: {e}")
        return desired


def _ensure_remote(repo: Repo) -> None:
    """
    Make sure 'origin' exists and uses a URL with credentials.
    Priority:
      1) GIT_REMOTE (recommended): e.g. https://oauth2:${GH_TOKEN}@github.com/user/repo.git
      2) Else, if GH_TOKEN set and origin is https, rewrite URL to include token.
    """
    try:
        token = os.getenv("GH_TOKEN", "").strip()
        configured_remote = os.getenv("GIT_REMOTE", "").strip()

        if "origin" in [r.name for r in repo.remotes]:
            origin = repo.remote("origin")
        else:
            if not configured_remote:
                print("❌ No 'origin' remote and GIT_REMOTE not provided; cannot push.")
                return
            origin = repo.create_remote("origin", configured_remote)

        # If GIT_REMOTE is provided, use it as source of truth
        if configured_remote:
            if origin.url != configured_remote:
                repo.git.remote("set-url", "origin", configured_remote)
            return

        # Else, inject token into existing HTTPS URL
        if token and origin.url.startswith("https://"):
            authed = origin.url
            if "@github.com" in authed:
                prefix, rest = authed.split("@github.com", 1)
                if "://" in prefix:
                    scheme = prefix.split("://", 1)[0]
                    authed = f"{scheme}://oauth2:{token}@github.com{rest}"
            else:
                authed = authed.replace("https://", f"https://oauth2:{token}@", 1)
            if origin.url != authed:
                repo.git.remote("set-url", "origin", authed)
    except Exception as e:
        print(f"⚠️ ensure_remote failed: {e}")


# ---------------------------
# Locks
# ---------------------------

def cancel_push_in_progress():
    """Forcefully cancel any ongoing push process & remove stale git lock if present."""
    if PUSH_LOCK.exists():
        try:
            PUSH_LOCK.unlink()
            print("🛑 Cancelled previous push in progress.")
        except Exception as e:
            print(f"⚠️ Could not remove push lock: {e}")

    if LOCK_FILE.exists():
        try:
            LOCK_FILE.unlink()
            print("⚠️ Removed stale Git index lock.")
        except Exception as e:
            print(f"⚠️ Could not remove Git lock: {e}")


# ---------------------------
# Commit & push (single, authoritative implementation)
# ---------------------------

def commit_and_push_changes(message: str, paths: Optional[Iterable[Path]] = None):
    """
    Commit and push repo changes.
    - If `paths` is provided, stage only those; otherwise stage all.
    - Ensures branch + remote credentials before pushing.
    - Respects DISABLE_GIT_PUSH=1 to skip push in certain envs.
    """
    if os.getenv("DISABLE_GIT_PUSH") == "1":
        print("⏩ DISABLE_GIT_PUSH=1 set — skipping commit/push.")
        return

    cancel_push_in_progress()
    PUSH_LOCK.touch()

    try:
        repo = _repo_or_none()
        if not repo:
            return

        _git_config(repo)
        branch = _ensure_branch(repo)
        _ensure_remote(repo)

        # Stage specific paths or all
        if paths:
            for p in paths:
                try:
                    repo.git.add(str(p))
                except GitCommandError as e:
                    print(f"⚠️ git add failed for {p}: {e}")
        else:
            repo.git.add(all=True)

        # Commit if anything changed
        if repo.is_dirty(untracked_files=True):
            repo.index.commit(message)
            print(f"✅ Committed: {message}")
        else:
            print("ℹ️ No changes to commit.")

        # Push (explicit refspec ensures branch:branch update)
        try:
            origin = repo.remote("origin")
            origin.push(refspec=f"{branch}:{branch}")
            print(f"🚀 Pushed to origin/{branch}.")
        except Exception as e:
            print(f"❌ Push failed: {e}")

    except GitCommandError as e:
        print(f"❌ Git error: {e}")
    finally:
        try:
            if PUSH_LOCK.exists():
                PUSH_LOCK.unlink()
        except Exception:
            pass


# ---------------------------
# Delete helpers
# ---------------------------

def delete_paths(paths: Iterable[Path]) -> List[Path]:
    """Delete paths if present (file or dir). Returns list of removed paths."""
    deleted: List[Path] = []
    for p in paths:
        if _safe_remove(p):
            deleted.append(p)
        else:
            print(f"⚠️ Not found: {p}")
    return deleted


def delete_set_and_push(set_name: str):
    """Delete a single set (flat JSON + generated pages + static) and push."""
    paths = _set_paths_for_delete(set_name)
    deleted = delete_paths(paths)
    if deleted:
        commit_and_push_changes(f"🗑️ Deleted set: {set_name}", paths=deleted)
    else:
        print(f"ℹ️ Nothing to delete for set '{set_name}'.")


def delete_multiple_sets_and_push(set_names: Iterable[str]):
    """Delete multiple sets and push in a single commit."""
    all_deleted: List[Path] = []
    for name in set_names:
        all_deleted.extend(delete_paths(_set_paths_for_delete(name)))

    if all_deleted:
        commit_and_push_changes(
            f"🗑️ Deleted sets: {', '.join(set_names)}",
            paths=all_deleted,
        )
    else:
        print("ℹ️ Nothing to delete.")
