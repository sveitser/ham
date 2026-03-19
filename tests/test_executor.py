from pathlib import Path
from unittest.mock import patch

import pytest

from ham.actions import (
    Action,
    CloseWindow,
    ExecProcess,
    GitWorktreeAdd,
    GitWorktreeRemove,
    LaunchProcess,
    PromptConfirmation,
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


def test_launch_process() -> None:
    action = LaunchProcess(cmd=["alacritty", "-e", "claude"], cwd=WT)
    with patch("ham.executor.subprocess.Popen") as mock_popen:
        execute([action])
    mock_popen.assert_called_once()
    _, kwargs = mock_popen.call_args
    assert kwargs["cwd"] == str(WT)
    assert kwargs["start_new_session"] is True


def test_close_window() -> None:
    action = CloseWindow(address="0xdead")
    with patch("ham.executor.subprocess.run") as mock_run:
        execute([action])
    mock_run.assert_called_once_with(
        ["hyprctl", "dispatch", "closewindow", "address:0xdead"],
        check=True,
    )


def test_exec_process() -> None:
    action = ExecProcess(cmd=["claude", "--continue"], cwd=WT)
    with (
        patch("ham.executor.os.chdir") as mock_chdir,
        patch("ham.executor.os.execvp") as mock_execvp,
    ):
        execute([action])
    mock_chdir.assert_called_once_with(WT)
    mock_execvp.assert_called_once_with("claude", ["claude", "--continue"])


def test_prompt_confirmation_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "y")
    execute([PromptConfirmation(message="proceed?")])


def test_prompt_confirmation_no(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "n")
    with pytest.raises(SystemExit, match="aborted"):
        execute([PromptConfirmation(message="proceed?")])


def test_unknown_action_raises() -> None:
    class FakeAction(Action):
        pass

    with pytest.raises(TypeError, match="unknown action"):
        execute([FakeAction()])
