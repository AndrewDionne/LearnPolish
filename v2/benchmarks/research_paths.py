"""Placement policy for local pronunciation-study files.

The owner may keep them in the Git-ignored repository root `temp/`, or in
any private folder outside Git. Never allow generated research files in
tracked application assets, source, or documentation directories.

Gitignore is an accident-prevention mechanism, not encryption/access control:
git add -f can still publish ignored material.
"""
from __future__ import annotations

from pathlib import Path


def check_research_location(path: Path, repository: Path | None = None) -> None:
    root = repository.resolve() if repository else Path(__file__).resolve().parents[2]
    location = path.absolute().resolve(strict=False)
    if location == root or root in location.parents:
        temp = root / "temp"
        if temp.is_symlink() or temp not in location.parents:
            raise ValueError(
                "Keep research data outside Git or under the ignored repo/temp/ "
                "directory; repo/assets/ and other tracked folders are not permitted"
            )
