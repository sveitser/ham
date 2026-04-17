from pathlib import Path
from unittest.mock import patch

import pytest

from ham.actions import (
    CloseWindow,
    GitWorktreeAdd,
    GitWorktreeRemove,
    LaunchProcess,
    PromptConfirmation,
    SetupDirenv,
    SwitchWorkspace,
)
from ham.git import worktree_path
from ham.hyprland import HyprlandWindow, get_workspace_for_windows, windows_in_path
from ham.orchestrator import plan_close, plan_delete, plan_open, plan_switch

REPO = Path("/fake/repo")
WS_ID = 5


def test_open_create_worktree_ok() -> None:
    actions = plan_open(
        REPO,
        "my-feature",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        workspace_id=WS_ID,
    )
    assert isinstance(actions[0], GitWorktreeAdd)
    assert actions[0].create_branch is True
    assert isinstance(actions[1], SetupDirenv)
    assert len([a for a in actions if isinstance(a, LaunchProcess)]) == 3


def test_open_reuse_worktree_ok() -> None:
    actions = plan_open(
        REPO,
        "my-feature",
        is_git_repo=True,
        worktree_exists=True,
        branch_exists=True,
        workspace_id=WS_ID,
    )
    assert not any(isinstance(a, GitWorktreeAdd) for a in actions)
    assert isinstance(actions[0], SetupDirenv)


def test_open_launch_apps_new_worktree() -> None:
    wt_path = worktree_path(REPO, "feat")
    actions = plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        workspace_id=WS_ID,
    )
    launches = [a for a in actions if isinstance(a, LaunchProcess)]
    assert launches[0].cmd == ["alacritty", "--working-directory", str(wt_path)]
    assert launches[1].cmd == ["emacs", "--chdir", str(wt_path), "."]
    assert launches[2].cmd == [
        "alacritty",
        "--working-directory",
        str(wt_path),
        "-e",
        "claude",
    ]


def test_open_launch_apps_existing_worktree() -> None:
    wt_path = worktree_path(REPO, "feat")
    actions = plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=True,
        branch_exists=True,
        workspace_id=WS_ID,
    )
    launches = [a for a in actions if isinstance(a, LaunchProcess)]
    assert launches[0].cmd == ["alacritty", "--working-directory", str(wt_path)]
    assert launches[1].cmd == ["emacs", "--chdir", str(wt_path), "."]
    assert launches[2].cmd == [
        "alacritty",
        "--working-directory",
        str(wt_path),
        "-e",
        "claude",
        "--continue",
    ]


def test_open_sanitize_branch_ok() -> None:
    actions = plan_open(
        REPO,
        "test/sanitize",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        workspace_id=WS_ID,
    )
    wt_add = actions[0]
    assert isinstance(wt_add, GitWorktreeAdd)
    assert wt_add.worktree_path == worktree_path(REPO, "test/sanitize")


def test_close_match_windows_ok() -> None:
    wt_path = worktree_path(REPO, "feat")
    windows = [
        HyprlandWindow(
            address="0x1", pid=1, class_name="alacritty", title="t", cwds=[wt_path]
        ),
        HyprlandWindow(
            address="0x2",
            pid=2,
            class_name="alacritty",
            title="t",
            cwds=[wt_path / "sub"],
        ),
    ]
    actions = plan_close(REPO, "feat", windows)
    assert len(actions) == 2
    assert all(isinstance(a, CloseWindow) for a in actions)


def test_close_skip_unrelated_ok() -> None:
    windows = [
        HyprlandWindow(
            address="0x1",
            pid=1,
            class_name="alacritty",
            title="t",
            cwds=[Path("/tmp/other")],
        ),
    ]
    actions = plan_close(REPO, "feat", windows)
    assert len(actions) == 0


def test_close_matches_descendant_cwd() -> None:
    """Regression: terminal whose own cwd is ~ but has a child (claude) in worktree."""
    wt_path = worktree_path(REPO, "feat")
    windows = [
        HyprlandWindow(
            address="0x1",
            pid=1,
            class_name="alacritty",
            title="t",
            cwds=[Path("/home/user"), wt_path],
        ),
    ]
    actions = plan_close(REPO, "feat", windows)
    assert len(actions) == 1
    assert isinstance(actions[0], CloseWindow)


def test_delete_clean_remove_ok() -> None:
    actions = plan_delete(
        REPO, "cleanup", worktree_exists=True, dirty=False, status="", windows=[]
    )
    assert len(actions) == 1
    assert isinstance(actions[0], GitWorktreeRemove)


def test_delete_dirty_prompt_ok() -> None:
    actions = plan_delete(
        REPO,
        "dirty",
        worktree_exists=True,
        dirty=True,
        status="?? untracked.txt",
        windows=[],
    )
    assert len(actions) == 2
    assert isinstance(actions[0], PromptConfirmation)
    assert isinstance(actions[1], GitWorktreeRemove)


def test_delete_closes_windows() -> None:
    wt_path = worktree_path(REPO, "with-windows")
    windows = [
        HyprlandWindow(
            address="0x1", pid=1, class_name="alacritty", title="t", cwds=[wt_path]
        ),
    ]
    actions = plan_delete(
        REPO,
        "with-windows",
        worktree_exists=True,
        dirty=False,
        status="",
        windows=windows,
    )
    assert isinstance(actions[0], CloseWindow)
    assert isinstance(actions[-1], GitWorktreeRemove)


def test_open_invalid_repo_fails() -> None:
    with pytest.raises(ValueError, match="not a git repository"):
        plan_open(
            REPO,
            "branch",
            is_git_repo=False,
            worktree_exists=False,
            branch_exists=False,
            workspace_id=WS_ID,
        )


def test_open_branch_exists_ok() -> None:
    actions = plan_open(
        REPO,
        "existing",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=True,
        workspace_id=WS_ID,
    )
    wt_add = actions[0]
    assert isinstance(wt_add, GitWorktreeAdd)
    assert wt_add.create_branch is False


def test_close_no_windows_ok() -> None:
    actions = plan_close(REPO, "feat", [])
    assert actions == []


def test_delete_worktree_missing_fails() -> None:
    with pytest.raises(ValueError, match="worktree does not exist"):
        plan_delete(
            REPO,
            "nonexistent",
            worktree_exists=False,
            dirty=False,
            status="",
            windows=[],
        )


def test_open_no_continue_new_worktree() -> None:
    actions = plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        workspace_id=WS_ID,
    )
    claude_launch = actions[-1]
    assert isinstance(claude_launch, LaunchProcess)
    assert "--continue" not in claude_launch.cmd


def test_open_claude_is_last() -> None:
    wt_path = worktree_path(REPO, "feat")
    actions = plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        workspace_id=WS_ID,
    )
    assert isinstance(actions[-1], LaunchProcess)
    assert actions[-1].cmd == [
        "alacritty",
        "--working-directory",
        str(wt_path),
        "-e",
        "claude",
    ]


def test_close_own_window_last() -> None:
    """Regression: own terminal must be closed last to avoid killing ham mid-run."""
    wt_path = worktree_path(REPO, "feat")
    own_pid = 100
    other_pid = 200
    windows = [
        HyprlandWindow(
            address="0x1",
            pid=own_pid,
            class_name="alacritty",
            title="t",
            cwds=[wt_path],
        ),
        HyprlandWindow(
            address="0x2", pid=other_pid, class_name="emacs", title="t", cwds=[wt_path]
        ),
    ]
    with patch("ham.hyprland._ancestor_pids", return_value={own_pid: 2}):
        result = windows_in_path(windows, wt_path)
    assert len(result) == 2
    assert result[-1].pid == own_pid
    assert result[0].pid == other_pid


def test_close_ancestors_ordered_by_distance() -> None:
    """Regression: closest ancestor (own terminal) closed last, distant ones first."""
    wt_path = worktree_path(REPO, "feat")
    distant_pid = 100  # claude terminal (further ancestor)
    close_pid = 101  # scratch terminal (direct parent)
    other_pid = 200  # emacs
    windows = [
        HyprlandWindow(
            address="0x1",
            pid=distant_pid,
            class_name="alacritty",
            title="claude",
            cwds=[wt_path],
        ),
        HyprlandWindow(
            address="0x2", pid=other_pid, class_name="emacs", title="t", cwds=[wt_path]
        ),
        HyprlandWindow(
            address="0x3",
            pid=close_pid,
            class_name="alacritty",
            title="scratch",
            cwds=[wt_path],
        ),
    ]
    with patch(
        "ham.hyprland._ancestor_pids", return_value={close_pid: 2, distant_pid: 5}
    ):
        result = windows_in_path(windows, wt_path)
    assert len(result) == 3
    assert result[0].pid == other_pid
    assert result[1].pid == distant_pid
    assert result[2].pid == close_pid


def test_switch_focus_existing_ok() -> None:
    """REQ:switch-focus-existing: windows exist, produces SwitchWorkspace."""
    actions = plan_switch(
        REPO,
        "feat",
        workspace_id=3,
        free_workspace=5,
        is_git_repo=True,
        worktree_exists=True,
        branch_exists=True,
    )
    assert actions == [SwitchWorkspace(workspace_id=3)]


def test_switch_open_new_ok() -> None:
    """REQ:switch-open-new: no windows, produces open actions then SwitchWorkspace last."""
    actions = plan_switch(
        REPO,
        "feat",
        workspace_id=None,
        free_workspace=5,
        is_git_repo=True,
        worktree_exists=True,
        branch_exists=True,
    )
    assert isinstance(actions[-1], SwitchWorkspace)
    assert actions[-1].workspace_id == 5
    assert len(actions) > 1
    assert not isinstance(actions[0], SwitchWorkspace)


def test_get_workspace_for_windows_empty() -> None:
    assert get_workspace_for_windows([]) is None


def test_get_workspace_for_windows_returns_first() -> None:
    windows = [
        HyprlandWindow(
            address="0x1", pid=1, class_name="alacritty", title="t", workspace_id=3
        ),
        HyprlandWindow(
            address="0x2", pid=2, class_name="emacs", title="t", workspace_id=5
        ),
    ]
    assert get_workspace_for_windows(windows) == 3


def test_launch_workspace_pin_ok() -> None:
    """TEST:launch-workspace-pin-ok: plan_open creates LaunchProcess with correct workspace_id."""
    actions = plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        workspace_id=7,
    )
    launches = [a for a in actions if isinstance(a, LaunchProcess)]
    assert len(launches) == 3
    assert all(lp.workspace_id == 7 for lp in launches)


def test_launch_cwd_ok() -> None:
    """TEST:launch-cwd-ok: plan_open embeds --working-directory in alacritty cmds and absolute path for emacs."""
    wt_path = worktree_path(REPO, "feat")
    actions = plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=True,
        branch_exists=True,
        workspace_id=WS_ID,
    )
    launches = [a for a in actions if isinstance(a, LaunchProcess)]
    # alacritty terminal
    assert "--working-directory" in launches[0].cmd
    assert str(wt_path) in launches[0].cmd
    # emacs gets absolute path
    assert launches[1].cmd == ["emacs", "--chdir", str(wt_path), "."]
    # claude alacritty
    assert "--working-directory" in launches[2].cmd
    assert str(wt_path) in launches[2].cmd


def test_switch_order_ok() -> None:
    """TEST:switch-order-ok: plan_switch puts SwitchWorkspace as last action."""
    actions = plan_switch(
        REPO,
        "feat",
        workspace_id=None,
        free_workspace=5,
        is_git_repo=True,
        worktree_exists=True,
        branch_exists=True,
    )
    assert isinstance(actions[-1], SwitchWorkspace)
    for a in actions[:-1]:
        assert not isinstance(a, SwitchWorkspace)


def test_launch_claude_continue_ok() -> None:
    """TEST:launch-claude-continue-ok: existing worktree cmd includes --continue."""
    actions = plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=True,
        branch_exists=True,
        workspace_id=WS_ID,
    )
    claude_launch = actions[-1]
    assert isinstance(claude_launch, LaunchProcess)
    assert "--continue" in claude_launch.cmd


def test_launch_new_worktree_ok() -> None:
    """TEST:launch-new-worktree-ok: GitWorktreeAdd precedes LaunchProcess actions."""
    actions = plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        workspace_id=WS_ID,
    )
    wt_idx = next(i for i, a in enumerate(actions) if isinstance(a, GitWorktreeAdd))
    first_launch_idx = next(
        i for i, a in enumerate(actions) if isinstance(a, LaunchProcess)
    )
    assert wt_idx < first_launch_idx
