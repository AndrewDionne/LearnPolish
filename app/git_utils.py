import os
import shutil
import time
from pathlib import Path
from git import Repo
from git.exc import GitCommandError

# === Constants ===
REPO_PATH = Path(__file__).resolve().parent.parent
LOCK_FILE = REPO_PATH / ".git/index.lock"
PUSH_LOCK = REPO_PATH / ".push_in_progress"

# === Cancel Any Running Push ===
def cancel_push_in_progress():
    """Forcefully cancel any ongoing push process."""
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

# === Commit & Push ===
def commit_and_push_changes(message: str):
    """Commit and push changes to GitHub, cancelling any ongoing push."""
    # 1. Cancel any in-progress push immediately
    cancel_push_in_progress()

    # 2. Create push lock for this push
    PUSH_LOCK.touch()

    try:
        repo = Repo(REPO_PATH)

        repo.git.add(all=True)
        if repo.is_dirty(untracked_files=True):
            repo.index.commit(message)
            origin = repo.remote(name="origin")
            origin.push()
            print("✅ Changes committed and pushed.")
        else:
            print("ℹ️ No changes to commit.")

    except GitCommandError as e:
        print(f"❌ Git error: {e}")
    finally:
        # Always remove push lock
        if PUSH_LOCK.exists():
            PUSH_LOCK.unlink()

# === Delete Helpers ===
def delete_paths(paths):
    """Delete a list of paths from the repo if they exist."""
    deleted_paths = []
    for path in paths:
        if path.exists():
            shutil.rmtree(path)
            deleted_paths.append(path)
            print(f"🧹 Deleted: {path}")
        else:
            print(f"⚠️ Not found: {path}")
    return deleted_paths

def delete_multiple_sets_and_push(set_names):
    """Delete multiple sets and push changes."""
    for set_name in set_names:
        paths = [
            REPO_PATH / "docs" / "output" / set_name,
            REPO_PATH / "docs" / "static" / set_name,
            REPO_PATH / "docs" / "sets" / set_name
        ]
        delete_paths(paths)

    commit_and_push_changes(f"🗑️ Deleted sets: {', '.join(set_names)}")

def delete_set_and_push(set_name):
    """Delete a single set and push changes."""
    paths = [
        REPO_PATH / "docs" / "output" / set_name,
        REPO_PATH / "docs" / "static" / set_name,
        REPO_PATH / "docs" / "sets" / set_name
    ]
    delete_paths(paths)
    commit_and_push_changes(f"🗑️ Deleted flashcard set: {set_name}")
