import subprocess
from pathlib import Path


def sanitize_branch(branch: str) -> str:
    return branch.replace("/", "-")


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


def is_git_repo(path: Path) -> bool:  # pragma: no cover
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
