from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

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


def test_git_worktree_remove() -> None:
    action = GitWorktreeRemove(repo=REPO, worktree_path=WT)
    with patch("ham.executor.subprocess.run") as mock_run:
        execute([action])
    mock_run.assert_called_once_with(
        ["git", "-C", str(REPO), "worktree", "remove", str(WT)],
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
    mock_run.assert_called_once_with(["direnv", "allow"], cwd=str(tmp_path))


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
    action = CloseWindow(address="0xdead")
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
    action = SwitchWorkspace(workspace_id=3)
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
