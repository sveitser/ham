from pathlib import Path

from ham.actions import (
    Action,
    CloseWindow,
    GitWorktreeAdd,
    GitWorktreeRemove,
    LaunchProcess,
    PromptConfirmation,
)
from ham.git import sanitize_branch
from ham.hyprland import HyprlandWindow, windows_in_path


def plan_open(
    repo: Path,
    branch: str,
    *,
    is_git_repo: bool,
    worktree_exists: bool,
    branch_exists: bool,
) -> list[Action]:
    if not is_git_repo:
        raise ValueError(f"not a git repository: {repo}")

    sanitized = sanitize_branch(branch)
    worktree_path = repo / ".wt" / sanitized
    actions: list[Action] = []

    if not worktree_exists:
        actions.append(
            GitWorktreeAdd(
                repo=repo,
                worktree_path=worktree_path,
                branch=branch,
                create_branch=not branch_exists,
            )
        )

    actions.extend(
        [
            LaunchProcess(
                cmd=["alacritty", "-e", "claude", "--continue"], cwd=worktree_path
            ),
            LaunchProcess(cmd=["alacritty"], cwd=worktree_path),
            LaunchProcess(cmd=["emacs", "."], cwd=worktree_path),
        ]
    )

    return actions


def plan_close(repo: Path, branch: str, windows: list[HyprlandWindow]) -> list[Action]:
    sanitized = sanitize_branch(branch)
    worktree_path = repo / ".wt" / sanitized
    matching = windows_in_path(windows, worktree_path)
    return [CloseWindow(address=w.address) for w in matching]


def plan_delete(
    repo: Path,
    branch: str,
    *,
    worktree_exists: bool,
    dirty: bool,
    status: str,
) -> list[Action]:
    if not worktree_exists:
        sanitized = sanitize_branch(branch)
        raise ValueError(f"worktree does not exist: {repo / '.wt' / sanitized}")

    sanitized = sanitize_branch(branch)
    worktree_path = repo / ".wt" / sanitized
    actions: list[Action] = []

    if dirty:
        actions.append(PromptConfirmation(message=status))

    actions.append(GitWorktreeRemove(repo=repo, worktree_path=worktree_path))
    return actions
