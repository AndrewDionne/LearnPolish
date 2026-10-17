"""Placement policy for local Path to Polish research files.

The owner's established and FINAL local research directory is the repository
root PathToPolish-Private-AI/. Keep original recordings exactly where they are.
The grandfathered temp/ folder and external private folders still work.

Gitignore is not encryption and can be bypassed with git add -f.
"""
from __future__ import annotations

from pathlib import Path

RESEARCH_DIRS = ("PathToPolish-Private-AI", "temp")


def check_research_location(path: Path, repository: Path | None = None) -> None:
    """Reject writes into tracked repository paths and symlink escapes."""
    root = repository.resolve() if repository else Path(__file__).resolve().parents[2]
    target = path.absolute()
    resolved = target.resolve(strict=False)
    in_repo = target == root or root in target.parents
    resolved_in_repo = resolved == root or root in resolved.parents
    if not (in_repo or resolved_in_repo):
        return  # Private folders entirely outside the repository remain supported.
    for name in RESEARCH_DIRS:
        folder = root / name
        if (folder in target.parents and folder in resolved.parents and
                not folder.is_symlink()):
            return
    raise ValueError(
        "Research files in this repository belong in "
        "PathToPolish-Private-AI/ (or the grandfathered ignored temp/), "
        "not assets/, docs/, or other tracked source folders"
    )
