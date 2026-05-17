from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ham.actions import (
    Action,
    CloseWindow,
    GitWorktreeAdd,
    GitWorktreeRemove,
    PromptConfirmation,
    SetupDirenv,
    SwitchWorkspace,
)
from ham.git import worktree_path
from ham.hyprland import windows_in_path

if TYPE_CHECKING:
    from ham.backend import Backend


def _launch_actions(
    cwd: Path,
    *,
    claude_continue: bool,
    workspace_id: str,
    backend: Backend,
) -> list[Action]:
    return [
        SetupDirenv(cwd=cwd),
        *backend.layout_actions(cwd, workspace_id, claude_continue),
    ]


def plan_open(
    repo: Path,
    branch: str,
    *,
    is_git_repo: bool,
    worktree_exists: bool,
    branch_exists: bool,
    remote_branch_exists: bool = False,
    workspace_id: str,
    backend: Backend,
) -> list[Action]:
    if not is_git_repo:
        raise ValueError(f"not a git repository: {repo}")

    wt_path = worktree_path(repo, branch)
    actions: list[Action] = []

    if not worktree_exists:
        if branch_exists:
            create, start = False, None
        elif remote_branch_exists:
            create, start = True, f"origin/{branch}"
        else:
            create, start = True, None
        actions.append(
            GitWorktreeAdd(
                repo=repo,
                worktree_path=wt_path,
                branch=branch,
                create_branch=create,
                start_point=start,
            )
        )

    actions.extend(
        _launch_actions(
            wt_path,
            claude_continue=worktree_exists,
            workspace_id=workspace_id,
            backend=backend,
        )
    )
    return actions


def plan_open_repo(repo: Path, *, workspace_id: str, backend: Backend) -> list[Action]:
    return _launch_actions(
        repo, claude_continue=True, workspace_id=workspace_id, backend=backend
    )


def plan_close(path: Path, windows: list) -> list[Action]:
    matching = windows_in_path(windows, path)
    return [CloseWindow(window_id=w.window_id) for w in matching]


def plan_delete(
    repo: Path,
    branch: str,
    *,
    worktree_exists: bool,
    dirty: bool,
    status: str,
    windows: list,
) -> list[Action]:
    wt_path = worktree_path(repo, branch)

    if not worktree_exists:
        raise ValueError(f"worktree does not exist: {wt_path}")

    actions: list[Action] = plan_close(wt_path, windows)

    if dirty:
        actions.append(PromptConfirmation(message=status))

    actions.append(GitWorktreeRemove(repo=repo, worktree_path=wt_path, force=dirty))
    return actions


def plan_switch(
    repo: Path,
    branch: str,
    *,
    workspace_id: str | None,
    free_workspace: str,
    is_git_repo: bool,
    worktree_exists: bool,
    branch_exists: bool,
    remote_branch_exists: bool = False,
    backend: Backend,
) -> list[Action]:
    if workspace_id is not None:
        return [SwitchWorkspace(workspace_id=workspace_id)]
    return plan_open(
        repo,
        branch,
        is_git_repo=is_git_repo,
        worktree_exists=worktree_exists,
        branch_exists=branch_exists,
        remote_branch_exists=remote_branch_exists,
        workspace_id=free_workspace,
        backend=backend,
    ) + [SwitchWorkspace(workspace_id=free_workspace)]


def plan_switch_repo(
    repo: Path,
    *,
    workspace_id: str | None,
    free_workspace: str,
    backend: Backend,
) -> list[Action]:
    if workspace_id is not None:
        return [SwitchWorkspace(workspace_id=workspace_id)]
    return plan_open_repo(repo, workspace_id=free_workspace, backend=backend) + [
        SwitchWorkspace(workspace_id=free_workspace)
    ]
