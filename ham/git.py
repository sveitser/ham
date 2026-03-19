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


def _repo_path_from_worktree(wt_dir: Path) -> Path | None:  # pragma: no cover
    """Resolve the parent repo path from a worktree directory via git-common-dir."""
    result = subprocess.run(
        [
            "git",
            "-C",
            str(wt_dir),
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).parent


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
    wt = DATA_DIR / repo_id / branch
    repo = _repo_path_from_worktree(wt)
    if repo is None:
        return None
    return (repo, branch)


def resolve_worktree(selection: str) -> tuple[Path, str] | None:  # pragma: no cover
    """Resolve a 'repo_name/branch' selection to (repo_path, branch). Returns None if not found."""
    parts = selection.split("/", 1)
    if len(parts) != 2:
        return None
    repo_name, branch = parts
    for repo_dir in DATA_DIR.iterdir():
        if not repo_dir.is_dir():
            continue
        branch_dir = repo_dir / branch
        if not branch_dir.is_dir():
            continue
        repo_path = _repo_path_from_worktree(branch_dir)
        if repo_path is not None and repo_path.name == repo_name:
            return (repo_path, branch)
    return None


def list_worktrees() -> list[tuple[str, str]]:  # pragma: no cover
    """Scan DATA_DIR for worktree dirs, resolve repo name via git. Returns [(repo_name, branch), ...]."""
    if not DATA_DIR.exists():
        return []
    results = []
    for repo_dir in sorted(DATA_DIR.iterdir()):
        if not repo_dir.is_dir():
            continue
        for branch_dir in sorted(repo_dir.iterdir()):
            if not branch_dir.is_dir():
                continue
            repo_path = _repo_path_from_worktree(branch_dir)
            if repo_path is None:
                continue
            results.append((repo_path.name, branch_dir.name))
    return results


def is_git_repo(path: Path) -> bool:  # pragma: no cover
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
