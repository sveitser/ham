import os
import subprocess
from pathlib import Path

DATA_DIR = (
    Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "ham"
)


def sanitize_branch(branch: str) -> str:
    return branch.replace("/", "-")


def worktree_path(repo: Path, branch: str) -> Path:
    repo_id = str(repo.resolve()).strip("/").replace("/", "-")
    return DATA_DIR / repo_id / sanitize_branch(branch)


def worktree_exists(repo: Path, worktree_path: Path) -> bool:  # pragma: no cover
    result = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    resolved = str(worktree_path.resolve())
    for line in result.stdout.splitlines():
        if line.startswith("worktree ") and line[9:] == resolved:
            return True
    return False


def branch_exists(repo: Path, branch: str) -> bool:  # pragma: no cover
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", branch],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def is_dirty(worktree_path: Path) -> tuple[bool, str]:  # pragma: no cover
    result = subprocess.run(
        ["git", "-C", str(worktree_path), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    output = result.stdout.strip()
    return (bool(output), output)


def resolve_from_cwd() -> tuple[Path, str] | None:  # pragma: no cover
    """If cwd is inside a ham worktree, return (repo_path, sanitized_branch)."""
    cwd = Path.cwd().resolve()
    try:
        rel = cwd.relative_to(DATA_DIR.resolve())
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) < 2:
        return None
    repo_id, branch = parts[0], parts[1]
    # Find the actual repo by checking git's common dir
    wt = DATA_DIR / repo_id / branch
    result = subprocess.run(
        [
            "git",
            "-C",
            str(wt),
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    # git-common-dir gives e.g. /home/lulu/r/foo/.git
    repo = Path(result.stdout.strip()).parent
    return (repo, branch)


def is_git_repo(path: Path) -> bool:  # pragma: no cover
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
