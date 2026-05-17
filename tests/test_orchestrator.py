from pathlib import Path
from unittest.mock import MagicMock, patch

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
from ham.orchestrator import (
    plan_close,
    plan_delete,
    plan_open,
    plan_open_repo,
    plan_switch,
    plan_switch_repo,
)

REPO = Path("/fake/repo")
WS_ID = "5"


def _mock_backend():
    b = MagicMock()
    b.layout_actions = MagicMock(
        return_value=[LaunchProcess(cmd=["x"], workspace_id=WS_ID)]
    )
    return b


def test_open_create_worktree_ok() -> None:
    backend = _mock_backend()
    actions = plan_open(
        REPO,
        "my-feature",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        workspace_id=WS_ID,
        backend=backend,
    )
    assert isinstance(actions[0], GitWorktreeAdd)
    assert actions[0].create_branch is True
    assert isinstance(actions[1], SetupDirenv)
    assert len([a for a in actions if isinstance(a, LaunchProcess)]) == 1


def test_open_reuse_worktree_ok() -> None:
    backend = _mock_backend()
    actions = plan_open(
        REPO,
        "my-feature",
        is_git_repo=True,
        worktree_exists=True,
        branch_exists=True,
        workspace_id=WS_ID,
        backend=backend,
    )
    assert not any(isinstance(a, GitWorktreeAdd) for a in actions)
    assert isinstance(actions[0], SetupDirenv)


def test_open_launch_apps_new_worktree() -> None:
    wt_path = worktree_path(REPO, "feat")
    backend = _mock_backend()
    plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        workspace_id=WS_ID,
        backend=backend,
    )
    backend.layout_actions.assert_called_once_with(wt_path, WS_ID, False)


def test_open_launch_apps_existing_worktree() -> None:
    wt_path = worktree_path(REPO, "feat")
    backend = _mock_backend()
    plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=True,
        branch_exists=True,
        workspace_id=WS_ID,
        backend=backend,
    )
    backend.layout_actions.assert_called_once_with(wt_path, WS_ID, True)


def test_open_sanitize_branch_ok() -> None:
    backend = _mock_backend()
    actions = plan_open(
        REPO,
        "test/sanitize",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        workspace_id=WS_ID,
        backend=backend,
    )
    wt_add = actions[0]
    assert isinstance(wt_add, GitWorktreeAdd)
    assert wt_add.worktree_path == worktree_path(REPO, "test/sanitize")


def test_close_match_windows_ok() -> None:
    wt_path = worktree_path(REPO, "feat")
    windows = [
        HyprlandWindow(
            window_id="0x1", pid=1, class_name="alacritty", title="t", cwds=[wt_path]
        ),
        HyprlandWindow(
            window_id="0x2",
            pid=2,
            class_name="alacritty",
            title="t",
            cwds=[wt_path / "sub"],
        ),
    ]
    actions = plan_close(wt_path, windows)
    assert len(actions) == 2
    assert all(isinstance(a, CloseWindow) for a in actions)


def test_close_skip_unrelated_ok() -> None:
    wt_path = worktree_path(REPO, "feat")
    windows = [
        HyprlandWindow(
            window_id="0x1",
            pid=1,
            class_name="alacritty",
            title="t",
            cwds=[Path("/tmp/other")],
        ),
    ]
    actions = plan_close(wt_path, windows)
    assert len(actions) == 0


def test_close_matches_descendant_cwd() -> None:
    """Regression: terminal whose own cwd is ~ but has a child (claude) in worktree."""
    wt_path = worktree_path(REPO, "feat")
    windows = [
        HyprlandWindow(
            window_id="0x1",
            pid=1,
            class_name="alacritty",
            title="t",
            cwds=[Path("/home/user"), wt_path],
        ),
    ]
    actions = plan_close(wt_path, windows)
    assert len(actions) == 1
    assert isinstance(actions[0], CloseWindow)


def test_close_repo_path_ok() -> None:
    windows = [
        HyprlandWindow(
            window_id="0x1", pid=1, class_name="alacritty", title="t", cwds=[REPO]
        ),
        HyprlandWindow(
            window_id="0x2",
            pid=2,
            class_name="emacs",
            title="t",
            cwds=[REPO / "src"],
        ),
    ]
    actions = plan_close(REPO, windows)
    assert len(actions) == 2
    assert all(isinstance(a, CloseWindow) for a in actions)


def test_delete_clean_remove_ok() -> None:
    actions = plan_delete(
        REPO, "cleanup", worktree_exists=True, dirty=False, status="", windows=[]
    )
    assert len(actions) == 1
    remove = actions[0]
    assert isinstance(remove, GitWorktreeRemove)
    assert remove.force is False


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
    remove = actions[1]
    assert isinstance(remove, GitWorktreeRemove)
    assert remove.force is True


def test_delete_closes_windows() -> None:
    wt_path = worktree_path(REPO, "with-windows")
    windows = [
        HyprlandWindow(
            window_id="0x1", pid=1, class_name="alacritty", title="t", cwds=[wt_path]
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
    backend = _mock_backend()
    with pytest.raises(ValueError, match="not a git repository"):
        plan_open(
            REPO,
            "branch",
            is_git_repo=False,
            worktree_exists=False,
            branch_exists=False,
            workspace_id=WS_ID,
            backend=backend,
        )


def test_open_branch_exists_ok() -> None:
    backend = _mock_backend()
    actions = plan_open(
        REPO,
        "existing",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=True,
        workspace_id=WS_ID,
        backend=backend,
    )
    wt_add = actions[0]
    assert isinstance(wt_add, GitWorktreeAdd)
    assert wt_add.create_branch is False
    assert wt_add.start_point is None


def test_open_remote_branch_creates_tracking() -> None:
    backend = _mock_backend()
    actions = plan_open(
        REPO,
        "from-remote",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        remote_branch_exists=True,
        workspace_id=WS_ID,
        backend=backend,
    )
    wt_add = actions[0]
    assert isinstance(wt_add, GitWorktreeAdd)
    assert wt_add.create_branch is True
    assert wt_add.start_point == "origin/from-remote"


def test_open_local_branch_wins_over_remote() -> None:
    backend = _mock_backend()
    actions = plan_open(
        REPO,
        "shared",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=True,
        remote_branch_exists=True,
        workspace_id=WS_ID,
        backend=backend,
    )
    wt_add = actions[0]
    assert isinstance(wt_add, GitWorktreeAdd)
    assert wt_add.create_branch is False
    assert wt_add.start_point is None


def test_close_no_windows_ok() -> None:
    actions = plan_close(worktree_path(REPO, "feat"), [])
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
    backend = _mock_backend()
    plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        workspace_id=WS_ID,
        backend=backend,
    )
    wt_path = worktree_path(REPO, "feat")
    backend.layout_actions.assert_called_once_with(wt_path, WS_ID, False)


def test_open_claude_is_last() -> None:
    backend = _mock_backend()
    actions = plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        workspace_id=WS_ID,
        backend=backend,
    )
    assert isinstance(actions[-1], LaunchProcess)
    assert actions[-1].cmd == ["x"]


def test_close_own_window_last() -> None:
    """Regression: own terminal must be closed last to avoid killing ham mid-run."""
    wt_path = worktree_path(REPO, "feat")
    own_pid = 100
    other_pid = 200
    windows = [
        HyprlandWindow(
            window_id="0x1",
            pid=own_pid,
            class_name="alacritty",
            title="t",
            cwds=[wt_path],
        ),
        HyprlandWindow(
            window_id="0x2",
            pid=other_pid,
            class_name="emacs",
            title="t",
            cwds=[wt_path],
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
            window_id="0x1",
            pid=distant_pid,
            class_name="alacritty",
            title="claude",
            cwds=[wt_path],
        ),
        HyprlandWindow(
            window_id="0x2",
            pid=other_pid,
            class_name="emacs",
            title="t",
            cwds=[wt_path],
        ),
        HyprlandWindow(
            window_id="0x3",
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
    backend = _mock_backend()
    actions = plan_switch(
        REPO,
        "feat",
        workspace_id="3",
        free_workspace="5",
        is_git_repo=True,
        worktree_exists=True,
        branch_exists=True,
        backend=backend,
    )
    assert actions == [SwitchWorkspace(workspace_id="3")]


def test_switch_open_new_ok() -> None:
    """REQ:switch-open-new: no windows, produces open actions then SwitchWorkspace last."""
    backend = _mock_backend()
    actions = plan_switch(
        REPO,
        "feat",
        workspace_id=None,
        free_workspace="5",
        is_git_repo=True,
        worktree_exists=True,
        branch_exists=True,
        backend=backend,
    )
    assert isinstance(actions[-1], SwitchWorkspace)
    assert actions[-1].workspace_id == "5"
    assert len(actions) > 1
    assert not isinstance(actions[0], SwitchWorkspace)


def test_get_workspace_for_windows_empty() -> None:
    assert get_workspace_for_windows([]) is None


def test_get_workspace_for_windows_returns_first() -> None:
    windows = [
        HyprlandWindow(
            window_id="0x1", pid=1, class_name="alacritty", title="t", workspace_id=3
        ),
        HyprlandWindow(
            window_id="0x2", pid=2, class_name="emacs", title="t", workspace_id=5
        ),
    ]
    assert get_workspace_for_windows(windows) == "3"


def test_launch_workspace_pin_ok() -> None:
    """TEST:launch-workspace-pin-ok: plan_open creates LaunchProcess with correct workspace_id."""
    backend = _mock_backend()
    plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        workspace_id="7",
        backend=backend,
    )
    backend.layout_actions.assert_called_once_with(
        worktree_path(REPO, "feat"), "7", False
    )


def test_launch_cwd_ok() -> None:
    """TEST:launch-cwd-ok: plan_open calls layout_actions with the worktree path."""
    wt_path = worktree_path(REPO, "feat")
    backend = _mock_backend()
    plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=True,
        branch_exists=True,
        workspace_id=WS_ID,
        backend=backend,
    )
    backend.layout_actions.assert_called_once_with(wt_path, WS_ID, True)


def test_switch_order_ok() -> None:
    """TEST:switch-order-ok: plan_switch puts SwitchWorkspace as last action."""
    backend = _mock_backend()
    actions = plan_switch(
        REPO,
        "feat",
        workspace_id=None,
        free_workspace="5",
        is_git_repo=True,
        worktree_exists=True,
        branch_exists=True,
        backend=backend,
    )
    assert isinstance(actions[-1], SwitchWorkspace)
    for a in actions[:-1]:
        assert not isinstance(a, SwitchWorkspace)


def test_launch_claude_continue_ok() -> None:
    """TEST:launch-claude-continue-ok: existing worktree calls layout_actions with claude_continue=True."""
    wt_path = worktree_path(REPO, "feat")
    backend = _mock_backend()
    plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=True,
        branch_exists=True,
        workspace_id=WS_ID,
        backend=backend,
    )
    backend.layout_actions.assert_called_once_with(wt_path, WS_ID, True)


def test_launch_new_worktree_ok() -> None:
    """TEST:launch-new-worktree-ok: GitWorktreeAdd precedes LaunchProcess actions."""
    backend = _mock_backend()
    actions = plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        workspace_id=WS_ID,
        backend=backend,
    )
    wt_idx = next(i for i, a in enumerate(actions) if isinstance(a, GitWorktreeAdd))
    first_launch_idx = next(
        i for i, a in enumerate(actions) if isinstance(a, LaunchProcess)
    )
    assert wt_idx < first_launch_idx


def test_open_repo_no_worktree_actions() -> None:
    backend = _mock_backend()
    actions = plan_open_repo(REPO, workspace_id=WS_ID, backend=backend)
    assert not any(isinstance(a, GitWorktreeAdd) for a in actions)
    assert isinstance(actions[0], SetupDirenv)
    assert actions[0].cwd == REPO
    backend.layout_actions.assert_called_once_with(REPO, WS_ID, True)


def test_open_repo_uses_repo_path() -> None:
    backend = _mock_backend()
    plan_open_repo(REPO, workspace_id=WS_ID, backend=backend)
    backend.layout_actions.assert_called_once_with(REPO, WS_ID, True)


def test_switch_repo_focus_existing() -> None:
    backend = _mock_backend()
    actions = plan_switch_repo(
        REPO, workspace_id="3", free_workspace="5", backend=backend
    )
    assert actions == [SwitchWorkspace(workspace_id="3")]


def test_switch_repo_open_new() -> None:
    backend = _mock_backend()
    actions = plan_switch_repo(
        REPO, workspace_id=None, free_workspace="5", backend=backend
    )
    assert isinstance(actions[-1], SwitchWorkspace)
    assert actions[-1].workspace_id == "5"
    assert any(isinstance(a, LaunchProcess) for a in actions)
    assert not any(isinstance(a, GitWorktreeAdd) for a in actions)


def test_switch_tmux_focus_existing() -> None:
    backend = _mock_backend()
    actions = plan_switch(
        REPO,
        "feat",
        workspace_id="myrepo-feat",
        free_workspace="myrepo-feat",
        is_git_repo=True,
        worktree_exists=True,
        branch_exists=True,
        backend=backend,
    )
    assert actions == [SwitchWorkspace(workspace_id="myrepo-feat")]


def test_switch_tmux_open_new() -> None:
    backend = _mock_backend()
    actions = plan_switch(
        REPO,
        "feat",
        workspace_id=None,
        free_workspace="myrepo-feat",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        backend=backend,
    )
    assert any(isinstance(a, LaunchProcess) for a in actions)
    assert actions[-1] == SwitchWorkspace(workspace_id="myrepo-feat")


def test_plan_open_calls_layout_actions() -> None:
    wt_path = worktree_path(REPO, "feat")
    backend = _mock_backend()
    plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        workspace_id=WS_ID,
        backend=backend,
    )
    backend.layout_actions.assert_called_once_with(wt_path, WS_ID, False)


def test_plan_open_repo_calls_layout_actions() -> None:
    backend = _mock_backend()
    plan_open_repo(REPO, workspace_id=WS_ID, backend=backend)
    backend.layout_actions.assert_called_once_with(REPO, WS_ID, True)
