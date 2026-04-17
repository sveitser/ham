from pathlib import Path

from ham.actions import (
    Action,
    CloseWindow,
    GitWorktreeAdd,
    GitWorktreeRemove,
    LaunchProcess,
    PromptConfirmation,
    SetupDirenv,
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
    workspace_id: int,
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
        claude_cmd = [
            "alacritty",
            "--working-directory",
            str(wt_path),
            "-e",
            "claude",
            "--continue",
        ]
    else:
        claude_cmd = ["alacritty", "--working-directory", str(wt_path), "-e", "claude"]

    actions.append(SetupDirenv(cwd=wt_path))

    actions.extend(
        [
            LaunchProcess(
                cmd=["alacritty", "--working-directory", str(wt_path)],
                workspace_id=workspace_id,
            ),
            LaunchProcess(
                cmd=["emacs", "--chdir", str(wt_path), "."],
                workspace_id=workspace_id,
            ),
            LaunchProcess(cmd=claude_cmd, workspace_id=workspace_id),
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
    return plan_open(
        repo,
        branch,
        is_git_repo=is_git_repo,
        worktree_exists=worktree_exists,
        branch_exists=branch_exists,
        workspace_id=free_workspace,
    ) + [SwitchWorkspace(workspace_id=free_workspace)]
