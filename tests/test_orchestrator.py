from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ham.actions import (
    CloseWindow,
    GitSetBranchUpstream,
    GitWorktreeAdd,
    GitWorktreeRemove,
    LaunchProcess,
    PromptConfirmation,
    SetupDirenv,
    SwitchWorkspace,
)
from dataclasses import replace

from ham.config import AgentRule, Config
from ham.git import worktree_path
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


def _assert_layout(backend, cwd, workspace_id, cont):
    """layout_actions(cwd, workspace_id, cont, spec); ignore the spec arg."""
    backend.layout_actions.assert_called_once()
    args = backend.layout_actions.call_args[0]
    assert args[:3] == (cwd, workspace_id, cont)


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
    assert isinstance(actions[1], GitSetBranchUpstream)
    assert isinstance(actions[2], SetupDirenv)
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
    _assert_layout(backend, wt_path, WS_ID, False)


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
    _assert_layout(backend, wt_path, WS_ID, True)


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


def test_close_creates_close_actions() -> None:
    windows = [MagicMock(window_id="0x1"), MagicMock(window_id="0x2")]
    actions = plan_close(windows)
    assert len(actions) == 2
    assert all(isinstance(a, CloseWindow) for a in actions)
    assert [a.window_id for a in actions] == ["0x1", "0x2"]


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
    windows = [MagicMock(window_id="0x1")]
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


def test_open_new_branch_defaults_to_origin_main() -> None:
    actions = plan_open(
        REPO,
        "fresh",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        remote_branch_exists=False,
        workspace_id=WS_ID,
        backend=_mock_backend(),
    )
    wt_add = actions[0]
    assert isinstance(wt_add, GitWorktreeAdd)
    assert wt_add.create_branch is True
    assert wt_add.start_point == "origin/main"
    assert wt_add.no_track is True
    assert actions[1] == GitSetBranchUpstream(repo=REPO, branch="fresh")


def test_open_new_branch_tracks_origin_branch_not_start_point() -> None:
    """New branches must track origin/$branch even when started from origin/dev."""
    actions = plan_open(
        REPO,
        "feature",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        remote_branch_exists=False,
        start_point="origin/dev",
        workspace_id=WS_ID,
        backend=_mock_backend(),
    )
    wt_add = actions[0]
    assert isinstance(wt_add, GitWorktreeAdd)
    assert wt_add.no_track is True
    assert actions[1] == GitSetBranchUpstream(repo=REPO, branch="feature")


def test_open_existing_branch_no_upstream_action() -> None:
    actions = plan_open(
        REPO,
        "existing",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=True,
        workspace_id=WS_ID,
        backend=_mock_backend(),
    )
    assert not any(isinstance(a, GitSetBranchUpstream) for a in actions)
    wt_add = actions[0]
    assert isinstance(wt_add, GitWorktreeAdd)
    assert wt_add.no_track is False


def test_open_explicit_start_point_overrides_default() -> None:
    actions = plan_open(
        REPO,
        "fresh",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        remote_branch_exists=False,
        start_point="origin/dev",
        workspace_id=WS_ID,
        backend=_mock_backend(),
    )
    wt_add = actions[0]
    assert isinstance(wt_add, GitWorktreeAdd)
    assert wt_add.create_branch is True
    assert wt_add.start_point == "origin/dev"


def test_open_explicit_start_point_overrides_remote_tracking() -> None:
    actions = plan_open(
        REPO,
        "from-remote",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        remote_branch_exists=True,
        start_point="origin/dev",
        workspace_id=WS_ID,
        backend=_mock_backend(),
    )
    wt_add = actions[0]
    assert isinstance(wt_add, GitWorktreeAdd)
    assert wt_add.create_branch is True
    assert wt_add.start_point == "origin/dev"


def test_open_local_branch_ignores_start_point() -> None:
    actions = plan_open(
        REPO,
        "existing",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=True,
        start_point="origin/dev",
        workspace_id=WS_ID,
        backend=_mock_backend(),
    )
    wt_add = actions[0]
    assert isinstance(wt_add, GitWorktreeAdd)
    assert wt_add.create_branch is False
    assert wt_add.start_point is None


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
    actions = plan_close([])
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
    _assert_layout(backend, wt_path, WS_ID, False)


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
    _assert_layout(backend, worktree_path(REPO, "feat"), "7", False)


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
    _assert_layout(backend, wt_path, WS_ID, True)


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
    _assert_layout(backend, wt_path, WS_ID, True)


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
    _assert_layout(backend, REPO, WS_ID, True)


def test_open_repo_uses_repo_path() -> None:
    backend = _mock_backend()
    plan_open_repo(REPO, workspace_id=WS_ID, backend=backend)
    _assert_layout(backend, REPO, WS_ID, True)


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
    _assert_layout(backend, wt_path, WS_ID, False)


def test_plan_open_repo_calls_layout_actions() -> None:
    backend = _mock_backend()
    plan_open_repo(REPO, workspace_id=WS_ID, backend=backend)
    _assert_layout(backend, REPO, WS_ID, True)


def _spec_from_call(backend):
    return backend.layout_actions.call_args[0][3]


def test_open_passes_spec_with_default_agent_when_no_config() -> None:
    """config=None: layout_actions gets a spec whose agent_cmd is the default agent."""
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
    spec = _spec_from_call(backend)
    assert spec.agent_cmd == ["claude"]


def test_open_passes_spec_with_matched_rule_agent() -> None:
    """config with a matching [[agent]] rule: spec.agent_cmd reflects the rule."""
    config = replace(
        Config.defaults(),
        agent_rules=(AgentRule(pattern="/fake/*", command=["claude-sandbox"]),),
    )
    backend = _mock_backend()
    plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        workspace_id=WS_ID,
        backend=backend,
        config=config,
    )
    spec = _spec_from_call(backend)
    assert spec.agent_cmd == ["claude-sandbox"]


def test_open_agent_continue_default_forces_continue() -> None:
    """agent_continue_default=True forces --continue even for a new worktree."""
    config = replace(Config.defaults(), agent_continue_default=True)
    backend = _mock_backend()
    plan_open(
        REPO,
        "feat",
        is_git_repo=True,
        worktree_exists=False,
        branch_exists=False,
        workspace_id=WS_ID,
        backend=backend,
        config=config,
    )
    spec = _spec_from_call(backend)
    assert spec.agent_cmd == ["claude", "--continue"]
    assert backend.layout_actions.call_args[0][2] is True
