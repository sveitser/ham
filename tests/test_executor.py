from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock, call, patch

import pytest

from ham.actions import (
    Action,
    CloseWindow,
    GitSetBranchUpstream,
    GitWorktreeAdd,
    GitWorktreeRemove,
    LaunchProcess,
    PromptConfirmation,
    SetupDirenv,
    SwitchWorkspace,
    TmuxLayout,
)
from ham.executor import execute

REPO = Path("/fake/repo")
WT = REPO / ".wt" / "feat"


def test_git_worktree_add_new_branch() -> None:
    action = GitWorktreeAdd(
        repo=REPO, worktree_path=WT, branch="feat", create_branch=True
    )
    with patch("ham.executor.subprocess.run") as mock_run:
        execute([action])
    mock_run.assert_called_once_with(
        ["git", "-C", str(REPO), "worktree", "add", "-b", "feat", str(WT)],
        check=True,
    )


def test_git_worktree_add_existing_branch() -> None:
    action = GitWorktreeAdd(
        repo=REPO, worktree_path=WT, branch="feat", create_branch=False
    )
    with patch("ham.executor.subprocess.run") as mock_run:
        execute([action])
    mock_run.assert_called_once_with(
        ["git", "-C", str(REPO), "worktree", "add", str(WT), "feat"],
        check=True,
    )


def test_git_worktree_add_tracks_remote() -> None:
    action = GitWorktreeAdd(
        repo=REPO,
        worktree_path=WT,
        branch="feat",
        create_branch=True,
        start_point="origin/feat",
    )
    with patch("ham.executor.subprocess.run") as mock_run:
        execute([action])
    mock_run.assert_called_once_with(
        [
            "git",
            "-C",
            str(REPO),
            "worktree",
            "add",
            "-b",
            "feat",
            str(WT),
            "origin/feat",
        ],
        check=True,
    )


def test_git_worktree_add_no_track() -> None:
    action = GitWorktreeAdd(
        repo=REPO,
        worktree_path=WT,
        branch="feat",
        create_branch=True,
        start_point="origin/main",
        no_track=True,
    )
    with patch("ham.executor.subprocess.run") as mock_run:
        execute([action])
    mock_run.assert_called_once_with(
        [
            "git",
            "-C",
            str(REPO),
            "worktree",
            "add",
            "--no-track",
            "-b",
            "feat",
            str(WT),
            "origin/main",
        ],
        check=True,
    )


def test_git_set_branch_upstream() -> None:
    action = GitSetBranchUpstream(repo=REPO, branch="feat")
    with patch("ham.executor.subprocess.run") as mock_run:
        execute([action])
    assert mock_run.call_args_list[0].args[0] == [
        "git",
        "-C",
        str(REPO),
        "config",
        "branch.feat.remote",
        "origin",
    ]
    assert mock_run.call_args_list[1].args[0] == [
        "git",
        "-C",
        str(REPO),
        "config",
        "branch.feat.merge",
        "refs/heads/feat",
    ]


def test_git_worktree_remove() -> None:
    action = GitWorktreeRemove(repo=REPO, worktree_path=WT)
    with patch("ham.executor.subprocess.run") as mock_run:
        execute([action])
    mock_run.assert_called_once_with(
        ["git", "-C", str(REPO), "worktree", "remove", str(WT)],
        check=True,
    )


def test_git_worktree_remove_force() -> None:
    action = GitWorktreeRemove(repo=REPO, worktree_path=WT, force=True)
    with patch("ham.executor.subprocess.run") as mock_run:
        execute([action])
    mock_run.assert_called_once_with(
        ["git", "-C", str(REPO), "worktree", "remove", "--force", str(WT)],
        check=True,
    )


def test_setup_direnv_copies_envrc_example(tmp_path: Path) -> None:
    (tmp_path / ".envrc").write_text("source_env .envrc.local")
    (tmp_path / ".envrc.example").write_text("use flake")
    action = SetupDirenv(cwd=tmp_path)
    with patch(
        "ham.executor.subprocess.run", return_value=CompletedProcess([], 0)
    ) as mock_run:
        execute([action])
    assert (tmp_path / ".envrc.local").read_text() == "use flake"
    assert mock_run.call_args_list == [
        call(["direnv", "allow"], cwd=str(tmp_path)),
        call(["direnv", "exec", str(tmp_path), "true"], cwd=str(tmp_path)),
    ]


def test_setup_direnv_skips_copy_when_local_exists(tmp_path: Path) -> None:
    (tmp_path / ".envrc").write_text("source_env .envrc.local")
    (tmp_path / ".envrc.example").write_text("use flake")
    (tmp_path / ".envrc.local").write_text("custom")
    action = SetupDirenv(cwd=tmp_path)
    with patch(
        "ham.executor.subprocess.run", return_value=CompletedProcess([], 0)
    ) as mock_run:
        execute([action])
    assert (tmp_path / ".envrc.local").read_text() == "custom"
    assert mock_run.call_args_list == [
        call(["direnv", "allow"], cwd=str(tmp_path)),
        call(["direnv", "exec", str(tmp_path), "true"], cwd=str(tmp_path)),
    ]


def test_setup_direnv_skips_warm_when_allow_fails(tmp_path: Path) -> None:
    (tmp_path / ".envrc").write_text("use flake")
    action = SetupDirenv(cwd=tmp_path)
    with patch(
        "ham.executor.subprocess.run", return_value=CompletedProcess([], 1)
    ) as mock_run:
        execute([action])
    mock_run.assert_called_once_with(["direnv", "allow"], cwd=str(tmp_path))


def test_setup_direnv_no_envrc(tmp_path: Path) -> None:
    action = SetupDirenv(cwd=tmp_path)
    with patch("ham.executor.subprocess.run") as mock_run:
        execute([action])
    mock_run.assert_not_called()


def test_setup_direnv_failure_continues(tmp_path: Path) -> None:
    (tmp_path / ".envrc").write_text("use flake")
    action = SetupDirenv(cwd=tmp_path)
    with patch("ham.executor.subprocess.run", return_value=CompletedProcess([], 1)):
        execute([action])  # should not raise


def test_launch_process() -> None:
    action = LaunchProcess(cmd=["alacritty", "-e", "claude"], workspace_id=3)
    with patch("ham.executor.subprocess.run") as mock_run:
        execute([action])
    mock_run.assert_called_once_with(
        ["hyprctl", "dispatch", "exec", "[workspace 3 silent]", "alacritty -e claude"],
        check=True,
    )


def test_launch_process_path_with_spaces() -> None:
    action = LaunchProcess(
        cmd=["alacritty", "--working-directory", "/home/user/my projects/repo"],
        workspace_id=3,
    )
    with patch("ham.executor.subprocess.run") as mock_run:
        execute([action])
    mock_run.assert_called_once_with(
        [
            "hyprctl",
            "dispatch",
            "exec",
            "[workspace 3 silent]",
            "alacritty --working-directory '/home/user/my projects/repo'",
        ],
        check=True,
    )


def test_close_window() -> None:
    action = CloseWindow(window_id="0xdead")
    with patch("ham.executor.subprocess.run") as mock_run:
        execute([action])
    mock_run.assert_called_once_with(
        ["hyprctl", "dispatch", "closewindow", "address:0xdead"],
        check=True,
    )


def test_prompt_confirmation_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "y")
    execute([PromptConfirmation(message="proceed?")])


def test_prompt_confirmation_no(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "n")
    with pytest.raises(SystemExit, match="aborted"):
        execute([PromptConfirmation(message="proceed?")])


def test_switch_workspace() -> None:
    action = SwitchWorkspace(workspace_id="3")
    with patch("ham.executor.subprocess.run") as mock_run:
        execute([action])
    mock_run.assert_called_once_with(
        ["hyprctl", "dispatch", "workspace", "3"],
        check=True,
    )


def test_unknown_action_raises() -> None:
    class FakeAction(Action):
        pass

    with pytest.raises(TypeError, match="unknown action"):
        execute([FakeAction()])


def test_tmux_layout_creates_session() -> None:
    action = TmuxLayout(
        session_name="myrepo-feat",
        cwd=Path("/tmp/wt"),
        emacs_cmd=["direnv", "exec", "/tmp/wt", "emacs", "/tmp/wt"],
        agent_cmd=["direnv", "exec", "/tmp/wt", "claude"],
    )
    with patch("ham.executor.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        execute([action])
    calls = [c.args[0] for c in mock_run.call_args_list]
    assert any("new-session" in str(c) for c in calls)
    assert not any("new-window" in str(c) for c in calls)


def test_tmux_layout_adds_window() -> None:
    action = TmuxLayout(
        session_name="myrepo-feat",
        cwd=Path("/tmp/wt"),
        emacs_cmd=["direnv", "exec", "/tmp/wt", "emacs", "/tmp/wt"],
        agent_cmd=["direnv", "exec", "/tmp/wt", "claude"],
    )
    with patch("ham.executor.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        execute([action])
    calls = [c.args[0] for c in mock_run.call_args_list]
    assert any("new-window" in str(c) for c in calls)
    assert not any("new-session" in str(c) for c in calls)


def test_tmux_layout_splits_and_sends() -> None:
    action = TmuxLayout(
        session_name="myrepo-feat",
        cwd=Path("/tmp/wt"),
        emacs_cmd=["direnv", "exec", "/tmp/wt", "emacs", "/tmp/wt"],
        agent_cmd=["direnv", "exec", "/tmp/wt", "claude"],
    )
    with patch("ham.executor.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        execute([action])
    calls = [c.args[0] for c in mock_run.call_args_list]
    split_calls = [c for c in calls if "split-window" in str(c)]
    assert len(split_calls) == 2
    assert any("-t" in c and "myrepo-feat:0.0" in c for c in split_calls)
    assert any("-t" in c and "myrepo-feat:0.1" in c for c in split_calls)
    send_calls = [c for c in calls if "send-keys" in str(c)]
    assert len(send_calls) == 2
    assert any("myrepo-feat:0.0" in c for c in send_calls)
    assert any("myrepo-feat:0.1" in c for c in send_calls)
    select_calls = [c for c in calls if "select-pane" in str(c)]
    assert len(select_calls) == 1
    assert "myrepo-feat:0.2" in select_calls[0]


def test_close_window_tmux() -> None:
    with patch("ham.executor.subprocess.run") as mock_run:
        execute([CloseWindow(window_id="myrepo-feat:0")], "tmux")
    mock_run.assert_called_once_with(
        ["tmux", "kill-window", "-t", "myrepo-feat:0"], check=True
    )


def test_switch_workspace_tmux_inside(monkeypatch) -> None:
    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,123,0")
    with patch("ham.executor.subprocess.run") as mock_run:
        execute([SwitchWorkspace(workspace_id="myrepo-feat")], "tmux")
    mock_run.assert_called_once_with(
        ["tmux", "switch-client", "-t", "myrepo-feat"], check=True
    )


def test_switch_workspace_tmux_outside(monkeypatch) -> None:
    monkeypatch.delenv("TMUX", raising=False)
    with patch("ham.executor.subprocess.run") as mock_run:
        execute([SwitchWorkspace(workspace_id="myrepo-feat")], "tmux")
    mock_run.assert_called_once_with(
        ["tmux", "attach-session", "-t", "myrepo-feat"], check=True
    )
