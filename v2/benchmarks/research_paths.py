"""Placement policy for local pronunciation-study files.

Users can keep research files in Git-ignored repository `temp/` or any
other private directory outside Git. Never write generated recordings,
model results or provider response files to tracked assets/source.

Gitignore prevents accidental staging; it is NOT encryption or protection
from `git add -f`, backup/sync software, or deliberately forced tracking.
"""
from __future__ import annotations

from pathlib import Path


def check_research_location(path: Path, repository: Path | None = None) -> None:
    root = repository.resolve() if repository else Path(__file__).resolve().parents[2]
    target = path.absolute()
    resolved = target.resolve(strict=False)
    temp = root / "temp"
    # Both the lexical and resolved path must reside under exactly repo/temp
    # whenever either address points into Git. Reject symlink escapes and
    # even external symlinks that resolve into tracked repository folders.
    in_repo = target == root or root in target.parents
    resolved_in_repo = resolved == root or root in resolved.parents
    if in_repo or resolved_in_repo:
        valid_target = temp in target.parents
        valid_resolved = temp in resolved.parents
        if (not valid_target or not valid_resolved or temp.is_symlink()):
            raise ValueError(
                "Keep research data outside Git or under ignored repo/temp/; "
                "repo/assets/ and other tracked folders are not permitted"
            )
