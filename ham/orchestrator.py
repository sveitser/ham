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


def _launch_actions(
    cwd: Path,
    *,
    claude_continue: bool,
    workspace_id: str,
    backend_type: str = "hyprland",
) -> list[Action]:
    direnv = ["direnv", "exec", str(cwd)]
    claude_cmd = direnv + ["claude"]
    if claude_continue:
        claude_cmd.append("--continue")
    if backend_type == "tmux":
        return [
            SetupDirenv(cwd=cwd),
            LaunchProcess(cmd=["bash"], workspace_id=workspace_id, cwd=cwd),
            LaunchProcess(cmd=claude_cmd, workspace_id=workspace_id, cwd=cwd),
        ]
    return [
        SetupDirenv(cwd=cwd),
        LaunchProcess(
            cmd=["alacritty", "--working-directory", str(cwd)],
            workspace_id=workspace_id,
        ),
        LaunchProcess(
            cmd=direnv + ["emacs", str(cwd / "README.md")],
            workspace_id=workspace_id,
        ),
        LaunchProcess(
            cmd=["alacritty", "--working-directory", str(cwd), "-e"] + claude_cmd,
            workspace_id=workspace_id,
        ),
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
    backend_type: str = "hyprland",
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
            backend_type=backend_type,
        )
    )
    return actions


def plan_open_repo(
    repo: Path, *, workspace_id: str, backend_type: str = "hyprland"
) -> list[Action]:
    return _launch_actions(
        repo, claude_continue=True, workspace_id=workspace_id, backend_type=backend_type
    )


def plan_close(repo: Path, branch: str, windows: list[HyprlandWindow]) -> list[Action]:
    wt_path = worktree_path(repo, branch)
    matching = windows_in_path(windows, wt_path)
    return [CloseWindow(window_id=w.window_id) for w in matching]


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
    backend_type: str = "hyprland",
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
        backend_type=backend_type,
    ) + [SwitchWorkspace(workspace_id=free_workspace)]


def plan_switch_repo(
    repo: Path,
    *,
    workspace_id: str | None,
    free_workspace: str,
    backend_type: str = "hyprland",
) -> list[Action]:
    if workspace_id is not None:
        return [SwitchWorkspace(workspace_id=workspace_id)]
    return plan_open_repo(
        repo, workspace_id=free_workspace, backend_type=backend_type
    ) + [SwitchWorkspace(workspace_id=free_workspace)]
