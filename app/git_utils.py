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
        # not found
        return False
    except Exception as e:
        print(f"⚠️ Failed to delete {p}: {e}")
        return False


def _set_paths_for_delete(set_name: str) -> List[Path]:
    """
    All paths we want to remove for a set:
      - docs/sets/<set>.json         (flat JSON)
      - docs/static/<set>/...        (audio etc.)
      - docs/<mode>/<set>/...        (generated pages per mode)
      - (legacy) docs/output/<set>/...
    """
    paths: List[Path] = [
        REPO_PATH / "docs" / "sets" / f"{set_name}.json",
        REPO_PATH / "docs" / "static" / set_name,
        REPO_PATH / "docs" / "output" / set_name,  # legacy; safe to remove if present
    ]
    for mode in MODES:
        paths.append(REPO_PATH / "docs" / mode / set_name)
    return paths


def _repo_or_none() -> Optional[Repo]:
    try:
        return Repo(REPO_PATH)
    except (InvalidGitRepositoryError, NoSuchPathError):
        print("ℹ️ Not a Git repository (skipping commit/push).")
        return None


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
# Commit & push
# ---------------------------

def commit_and_push_changes(message: str, paths: Optional[Iterable[Path]] = None):
    """
    Commit and push repo changes.
    - If `paths` is provided, stage only those; otherwise stage all.
    - Respects a PUSH lock to avoid concurrent pushes.
    - Skips commit/push if not a git repo.
    """
    # Environment override: disable pushing (useful in CI/dev)
    if os.getenv("DISABLE_GIT_PUSH") == "1":
        print("⏩ DISABLE_GIT_PUSH=1 set — skipping commit/push.")
        return

    cancel_push_in_progress()
    PUSH_LOCK.touch()

    try:
        repo = _repo_or_none()
        if not repo:
            return  # Not a repo, nothing to do

        # Stage
        if paths:
            for p in paths:
                try:
                    repo.git.add(str(p))
                except GitCommandError as e:
                    print(f"⚠️ git add failed for {p}: {e}")
        else:
            repo.git.add(all=True)

        # Commit if needed
        if repo.is_dirty(untracked_files=True):
            repo.index.commit(message)
            print(f"✅ Committed: {message}")
            # Push
            try:
                origin = repo.remote(name="origin")
                origin.push()
                print("🚀 Pushed to origin.")
            except Exception as e:
                print(f"❌ Push failed: {e}")
        else:
            print("ℹ️ No changes to commit.")
    except GitCommandError as e:
        print(f"❌ Git error: {e}")
    finally:
        if PUSH_LOCK.exists():
            PUSH_LOCK.unlink()


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
            paths=all_deleted
        )
    else:
        print("ℹ️ Nothing to delete.")
