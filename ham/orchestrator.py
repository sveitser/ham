from pathlib import Path

from ham.actions import (
    Action,
    CloseWindow,
    ExecProcess,
    GitWorktreeAdd,
    GitWorktreeRemove,
    LaunchProcess,
    PromptConfirmation,
    SwitchWorkspace,
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

    if worktree_exists:
        exec_action = ExecProcess(
            cmd=["claude", "--continue"], cwd=wt_path, fallback_cmd=["claude"]
        )
    else:
        exec_action = ExecProcess(cmd=["claude"], cwd=wt_path)

    actions.extend(
        [
            LaunchProcess(cmd=["alacritty"], cwd=wt_path),
            LaunchProcess(cmd=["emacs", "."], cwd=wt_path),
            exec_action,
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
    windows: list[HyprlandWindow],
) -> list[Action]:
    wt_path = worktree_path(repo, branch)

    if not worktree_exists:
        raise ValueError(f"worktree does not exist: {wt_path}")

    actions: list[Action] = plan_close(repo, branch, windows)

    if dirty:
        actions.append(PromptConfirmation(message=status))

    actions.append(GitWorktreeRemove(repo=repo, worktree_path=wt_path))
    return actions


def plan_switch(
    repo: Path,
    branch: str,
    *,
    workspace_id: int | None,
    free_workspace: int,
    is_git_repo: bool,
    worktree_exists: bool,
    branch_exists: bool,
) -> list[Action]:
    if workspace_id is not None:
        return [SwitchWorkspace(workspace_id=workspace_id)]
    return [SwitchWorkspace(workspace_id=free_workspace)] + plan_open(
        repo,
        branch,
        is_git_repo=is_git_repo,
        worktree_exists=worktree_exists,
        branch_exists=branch_exists,
    )
