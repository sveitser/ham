from pathlib import Path
from unittest.mock import patch

import pytest

from ham.cli import main

FAKE_WT = Path("/fake/wt")


def test_open_parses_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open", "/some/path", "my-branch"])
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_open", return_value=[]) as mock_plan,
        patch("ham.cli.execute") as mock_exec,
    ):
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = False
        mock_git.branch_exists.return_value = False
        main()
    mock_plan.assert_called_once()
    mock_exec.assert_called_once_with([])


def test_close_parses_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "close", "/some/path", "my-branch"])
    with (
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.hyprland") as mock_hyprland,
        patch("ham.cli.plan_close", return_value=[]) as mock_plan,
        patch("ham.cli.execute") as mock_exec,
    ):
        mock_hyprland.get_windows.return_value = []
        main()
    mock_plan.assert_called_once()
    mock_exec.assert_called_once_with([])


def test_delete_parses_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "delete", "/some/path", "my-branch"])
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_delete", return_value=[]) as mock_plan,
        patch("ham.cli.execute") as mock_exec,
    ):
        mock_git.worktree_exists.return_value = True
        mock_git.is_dirty.return_value = (False, "")
        main()
    mock_plan.assert_called_once()
    mock_exec.assert_called_once_with([])


def test_missing_subcommand_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham"])
    with pytest.raises(SystemExit):
        main()
