from pathlib import Path

import pytest

from ham.actions import (
    CloseWindow,
    GitWorktreeAdd,
    GitWorktreeRemove,
    LaunchProcess,
    PromptConfirmation,
)
from ham.hyprland import HyprlandWindow
from ham.orchestrator import plan_close, plan_delete, plan_open

REPO = Path("/fake/repo")


def test_open_create_worktree_ok() -> None:
    actions = plan_open(
        REPO, "my-feature", is_git_repo=True, worktree_exists=False, branch_exists=False
    )
    assert isinstance(actions[0], GitWorktreeAdd)
    assert actions[0].create_branch is True
    assert len([a for a in actions if isinstance(a, LaunchProcess)]) == 3


def test_open_reuse_worktree_ok() -> None:
    actions = plan_open(
        REPO, "my-feature", is_git_repo=True, worktree_exists=True, branch_exists=True
    )
    assert not any(isinstance(a, GitWorktreeAdd) for a in actions)
    assert len(actions) == 3


def test_open_launch_apps_ok() -> None:
    actions = plan_open(
        REPO, "feat", is_git_repo=True, worktree_exists=False, branch_exists=False
    )
    launches = [a for a in actions if isinstance(a, LaunchProcess)]
    assert launches[0].cmd == ["alacritty", "-e", "claude", "--continue"]
    assert launches[1].cmd == ["alacritty"]
    assert launches[2].cmd == ["emacs", "."]


def test_open_sanitize_branch_ok() -> None:
    actions = plan_open(
        REPO,
        "test/sanitize",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
    )
    wt_add = actions[0]
    assert isinstance(wt_add, GitWorktreeAdd)
    assert wt_add.worktree_path == REPO / ".wt" / "test-sanitize"


def test_close_match_windows_ok() -> None:
    worktree_path = REPO / ".wt" / "feat"
    windows = [
        HyprlandWindow(
            address="0x1", pid=1, class_name="alacritty", title="t", cwd=worktree_path
        ),
        HyprlandWindow(
            address="0x2",
            pid=2,
            class_name="alacritty",
            title="t",
            cwd=worktree_path / "sub",
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
            cwd=Path("/tmp/other"),
        ),
    ]
    actions = plan_close(REPO, "feat", windows)
    assert len(actions) == 0


def test_delete_clean_remove_ok() -> None:
    actions = plan_delete(REPO, "cleanup", worktree_exists=True, dirty=False, status="")
    assert len(actions) == 1
    assert isinstance(actions[0], GitWorktreeRemove)


def test_delete_dirty_prompt_ok() -> None:
    actions = plan_delete(
        REPO, "dirty", worktree_exists=True, dirty=True, status="?? untracked.txt"
    )
    assert len(actions) == 2
    assert isinstance(actions[0], PromptConfirmation)
    assert isinstance(actions[1], GitWorktreeRemove)


def test_open_invalid_repo_fails() -> None:
    with pytest.raises(ValueError, match="not a git repository"):
        plan_open(
            REPO,
            "branch",
            is_git_repo=False,
            worktree_exists=False,
            branch_exists=False,
        )


def test_open_branch_exists_ok() -> None:
    actions = plan_open(
        REPO, "existing", is_git_repo=True, worktree_exists=False, branch_exists=True
    )
    wt_add = actions[0]
    assert isinstance(wt_add, GitWorktreeAdd)
    assert wt_add.create_branch is False


def test_close_no_windows_ok() -> None:
    actions = plan_close(REPO, "feat", [])
    assert actions == []


def test_delete_worktree_missing_fails() -> None:
    with pytest.raises(ValueError, match="worktree does not exist"):
        plan_delete(REPO, "nonexistent", worktree_exists=False, dirty=False, status="")


def test_open_continue_flag_ok() -> None:
    actions = plan_open(
        REPO, "feat", is_git_repo=True, worktree_exists=False, branch_exists=False
    )
    claude_launch = [
        a for a in actions if isinstance(a, LaunchProcess) and "claude" in a.cmd
    ][0]
    assert "--continue" in claude_launch.cmd
