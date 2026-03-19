from pathlib import Path

from ham.actions import (
    Action,
    CloseWindow,
    GitWorktreeAdd,
    GitWorktreeRemove,
    LaunchProcess,
    PromptConfirmation,
)
from ham.git import worktree_path
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

    wt_path = worktree_path(repo, branch)
    actions: list[Action] = []

    if not worktree_exists:
        actions.append(
            GitWorktreeAdd(
                repo=repo,
                worktree_path=wt_path,
                branch=branch,
                create_branch=not branch_exists,
            )
        )

    claude_cmd = ["alacritty", "-e", "claude"]
    if worktree_exists:
        claude_cmd.append("--continue")

    actions.extend(
        [
            LaunchProcess(cmd=claude_cmd, cwd=wt_path),
            LaunchProcess(cmd=["alacritty"], cwd=wt_path),
            LaunchProcess(cmd=["emacs", "."], cwd=wt_path),
        ]
    )

    return actions


def plan_close(repo: Path, branch: str, windows: list[HyprlandWindow]) -> list[Action]:
    wt_path = worktree_path(repo, branch)
    matching = windows_in_path(windows, wt_path)
    return [CloseWindow(address=w.address) for w in matching]


def plan_delete(
    repo: Path,
    branch: str,
    *,
    worktree_exists: bool,
    dirty: bool,
    status: str,
) -> list[Action]:
    wt_path = worktree_path(repo, branch)

    if not worktree_exists:
        raise ValueError(f"worktree does not exist: {wt_path}")

    actions: list[Action] = []

    if dirty:
        actions.append(PromptConfirmation(message=status))

    actions.append(GitWorktreeRemove(repo=repo, worktree_path=wt_path))
    return actions
