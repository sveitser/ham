from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ham.actions import (
    Action,
    CloseWindow,
    GitSetBranchUpstream,
    GitWorktreeAdd,
    GitWorktreeRemove,
    PromptConfirmation,
    SetupDirenv,
    SwitchWorkspace,
)
from ham.config import Config, build_layout_spec
from ham.git import worktree_path

if TYPE_CHECKING:
    from ham.backend import Backend


def _launch_actions(
    cwd: Path,
    *,
    agent_continue: bool,
    workspace_id: str,
    backend: Backend,
    repo: Path,
    config: Config | None = None,
) -> list[Action]:
    cfg = config or Config.defaults()
    cont = agent_continue or cfg.agent_continue_default
    spec = build_layout_spec(cfg, repo, agent_continue=cont)
    return [
        SetupDirenv(cwd=cwd),
        *backend.layout_actions(cwd, workspace_id, cont, spec),
    ]


def plan_open(
    repo: Path,
    branch: str,
    *,
    is_git_repo: bool,
    worktree_exists: bool,
    branch_exists: bool,
    remote_branch_exists: bool = False,
    start_point: str | None = None,
    workspace_id: str,
    backend: Backend,
    config: Config | None = None,
) -> list[Action]:
    if not is_git_repo:
        raise ValueError(f"not a git repository: {repo}")

    wt_path = worktree_path(repo, branch)
    actions: list[Action] = []

    if not worktree_exists:
        if branch_exists:
            create, start = False, None
        elif start_point is not None:
            create, start = True, start_point
        elif remote_branch_exists:
            create, start = True, f"origin/{branch}"
        else:
            create, start = True, "origin/main"
        actions.append(
            GitWorktreeAdd(
                repo=repo,
                worktree_path=wt_path,
                branch=branch,
                create_branch=create,
                start_point=start,
                no_track=create,
            )
        )
        if create:
            actions.append(GitSetBranchUpstream(repo=repo, branch=branch))

    actions.extend(
        _launch_actions(
            wt_path,
            agent_continue=worktree_exists,
            workspace_id=workspace_id,
            backend=backend,
            repo=repo,
            config=config,
        )
    )
    return actions


def plan_open_repo(
    repo: Path,
    *,
    workspace_id: str,
    backend: Backend,
    config: Config | None = None,
) -> list[Action]:
    return _launch_actions(
        repo,
        agent_continue=True,
        workspace_id=workspace_id,
        backend=backend,
        repo=repo,
        config=config,
    )


def plan_close(windows: list) -> list[Action]:
    return [CloseWindow(window_id=w.window_id) for w in windows]


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

    actions: list[Action] = plan_close(windows)

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
    start_point: str | None = None,
    config: Config | None = None,
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
        start_point=start_point,
        workspace_id=free_workspace,
        backend=backend,
        config=config,
    ) + [SwitchWorkspace(workspace_id=free_workspace)]


def plan_switch_repo(
    repo: Path,
    *,
    workspace_id: str | None,
    free_workspace: str,
    backend: Backend,
    config: Config | None = None,
) -> list[Action]:
    if workspace_id is not None:
        return [SwitchWorkspace(workspace_id=workspace_id)]
    return plan_open_repo(
        repo, workspace_id=free_workspace, backend=backend, config=config
    ) + [SwitchWorkspace(workspace_id=free_workspace)]
