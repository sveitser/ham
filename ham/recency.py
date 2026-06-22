import os
import re
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"


def encode_project_dir(wt_path: Path) -> str:
    """Claude Code names a project's session dir after its cwd, every non-alphanumeric char as '-'."""
    return re.sub(r"[^a-zA-Z0-9]", "-", str(wt_path))


def last_session_mtime(
    wt_path: Path, projects_dir: Path = PROJECTS_DIR
) -> float | None:
    """Newest *.jsonl mtime in the worktree's Claude session dir, or None if none exist."""
    session_dir = projects_dir / encode_project_dir(wt_path)
    if not session_dir.is_dir():
        return None
    mtimes = [
        e.stat().st_mtime for e in os.scandir(session_dir) if e.name.endswith(".jsonl")
    ]
    return max(mtimes, default=None)


def format_age(epoch: float | None, now: float) -> str:
    """Relative age like '3m', '2h', '5d'; empty when epoch is None."""
    if epoch is None:
        return ""
    diff = now - epoch
    if diff < 60:
        return "now"
    if diff < 3600:
        return f"{int(diff // 60)}m"
    if diff < 86400:
        return f"{int(diff // 3600)}h"
    return f"{int(diff // 86400)}d"
