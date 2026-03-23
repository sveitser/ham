from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from ham.cli import main
from ham.hyprland import HyprlandWindow

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


def test_open_selection_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open", "myrepo/feat"])
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_open", return_value=[]) as mock_plan,
        patch("ham.cli.execute") as mock_exec,
    ):
        mock_git.resolve_worktree.return_value = (Path("/repo"), "feat")
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = False
        mock_git.branch_exists.return_value = False
        main()
    mock_git.resolve_worktree.assert_called_once_with("myrepo/feat")
    mock_plan.assert_called_once()
    mock_exec.assert_called_once_with([])


def test_open_selection_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open", "nope/nope"])
    with patch("ham.cli.git") as mock_git:
        mock_git.resolve_worktree.return_value = None
        with pytest.raises(SystemExit):
            main()


def test_open_no_args(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open"])
    with pytest.raises(SystemExit):
        main()


def test_open_selection_no_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open", "something"])
    with patch("ham.cli.git") as mock_git:
        mock_git.resolve_worktree.return_value = None
        with pytest.raises(SystemExit):
            main()


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
        patch("ham.cli.hyprland") as mock_hyprland,
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_delete", return_value=[]) as mock_plan,
        patch("ham.cli.execute") as mock_exec,
    ):
        mock_git.worktree_exists.return_value = True
        mock_git.is_dirty.return_value = (False, "")
        mock_hyprland.get_windows.return_value = []
        main()
    mock_plan.assert_called_once()
    mock_exec.assert_called_once_with([])


def test_close_no_args_resolves_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "close"])
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.hyprland") as mock_hyprland,
        patch("ham.cli.plan_close", return_value=[]) as mock_plan,
        patch("ham.cli.execute") as mock_exec,
    ):
        mock_git.resolve_from_cwd.return_value = (Path("/repo"), "feat")
        mock_hyprland.get_windows.return_value = []
        main()
    mock_plan.assert_called_once()
    mock_exec.assert_called_once_with([])


def test_close_no_args_not_in_worktree(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "close"])
    with patch("ham.cli.git") as mock_git:
        mock_git.resolve_from_cwd.return_value = None
        with pytest.raises(SystemExit):
            main()


def test_delete_no_args_resolves_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "delete"])
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.hyprland") as mock_hyprland,
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_delete", return_value=[]) as mock_plan,
        patch("ham.cli.execute") as mock_exec,
    ):
        mock_git.resolve_from_cwd.return_value = (Path("/repo"), "feat")
        mock_git.worktree_exists.return_value = True
        mock_git.is_dirty.return_value = (False, "")
        mock_hyprland.get_windows.return_value = []
        main()
    mock_plan.assert_called_once()
    mock_exec.assert_called_once_with([])


def test_missing_subcommand_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham"])
    with pytest.raises(SystemExit):
        main()


def test_list_prints_worktrees(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "list"])
    with patch("ham.cli.git") as mock_git:
        mock_git.list_worktrees.return_value = [("myrepo", "feat"), ("other", "main")]
        main()
    out = capsys.readouterr().out
    assert "myrepo/feat\n" in out
    assert "other/main\n" in out


def test_list_empty(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "list"])
    with patch("ham.cli.git") as mock_git:
        mock_git.list_worktrees.return_value = []
        main()
    out = capsys.readouterr().out
    assert out == ""


def test_switch_with_query(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "switch", "myrepo/feat"])
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.hyprland") as mock_hyprland,
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.windows_in_path", return_value=[]),
        patch("ham.cli.get_workspace_for_windows", return_value=None),
        patch("ham.cli.find_free_workspace", return_value=5),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute") as mock_exec,
    ):
        mock_git.list_worktrees.return_value = [("myrepo", "feat")]
        mock_git.resolve_worktree.return_value = (Path("/repo"), "feat")
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = True
        mock_git.branch_exists.return_value = True
        mock_hyprland.get_windows.return_value = []
        main()
    mock_plan.assert_called_once()
    mock_exec.assert_called_once_with([])


def test_switch_no_query_fzf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "switch"])
    fzf_result = CompletedProcess(
        args=["fzf"], returncode=0, stdout="myrepo/feat\n", stderr=""
    )
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.hyprland") as mock_hyprland,
        patch("ham.cli.subprocess.run", return_value=fzf_result) as mock_run,
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.windows_in_path", return_value=[]),
        patch("ham.cli.get_workspace_for_windows", return_value=None),
        patch("ham.cli.find_free_workspace", return_value=5),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.list_worktrees.return_value = [("myrepo", "feat")]
        mock_git.resolve_worktree.return_value = (Path("/repo"), "feat")
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = True
        mock_git.branch_exists.return_value = True
        mock_hyprland.get_windows.return_value = []
        main()
    mock_run.assert_called_once_with(
        ["fzf"], input="myrepo/feat", capture_output=True, text=True
    )
    mock_plan.assert_called_once()


def test_switch_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "switch", "nope/nope"])
    with patch("ham.cli.git") as mock_git:
        mock_git.list_worktrees.return_value = [("myrepo", "feat")]
        with pytest.raises(SystemExit):
            main()


def test_switch_no_worktrees(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "switch", "anything"])
    with patch("ham.cli.git") as mock_git:
        mock_git.list_worktrees.return_value = []
        with pytest.raises(SystemExit):
            main()


def test_rofi_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "rofi"])
    rofi_result = CompletedProcess(
        args=["rofi"], returncode=0, stdout="myrepo/feat\n", stderr=""
    )
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.hyprland") as mock_hyprland,
        patch("ham.cli.subprocess.run", return_value=rofi_result) as mock_run,
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.windows_in_path", return_value=[]),
        patch("ham.cli.get_workspace_for_windows", return_value=None),
        patch("ham.cli.find_free_workspace", return_value=5),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.list_worktrees.return_value = [("myrepo", "feat")]
        mock_git.resolve_worktree.return_value = (Path("/repo"), "feat")
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = True
        mock_git.branch_exists.return_value = True
        mock_hyprland.get_windows.return_value = []
        main()
    mock_run.assert_called_once_with(
        ["rofi", "-dmenu", "-p", "ham", "-i"],
        input="myrepo/feat",
        capture_output=True,
        text=True,
    )
    mock_plan.assert_called_once()


def test_rofi_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "rofi"])
    rofi_result = CompletedProcess(args=["rofi"], returncode=1, stdout="", stderr="")
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.subprocess.run", return_value=rofi_result),
    ):
        mock_git.list_worktrees.return_value = [("myrepo", "feat")]
        with pytest.raises(SystemExit):
            main()


def test_switch_existing_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    """workspace_id is not None, find_free_workspace should not be called."""
    monkeypatch.setattr("sys.argv", ["ham", "switch", "myrepo/feat"])
    window = HyprlandWindow(
        address="0x1", pid=1, class_name="alacritty", title="t", workspace_id=3
    )
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.hyprland") as mock_hyprland,
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.windows_in_path", return_value=[window]),
        patch("ham.cli.get_workspace_for_windows", return_value=3),
        patch("ham.cli.find_free_workspace") as mock_free,
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.list_worktrees.return_value = [("myrepo", "feat")]
        mock_git.resolve_worktree.return_value = (Path("/repo"), "feat")
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = True
        mock_git.branch_exists.return_value = True
        mock_hyprland.get_windows.return_value = [window]
        main()
    mock_free.assert_not_called()
    mock_plan.assert_called_once()
    call_kwargs = mock_plan.call_args
    assert call_kwargs[1]["workspace_id"] == 3
    assert call_kwargs[1]["free_workspace"] == 0


def test_switch_new_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    """workspace_id is None, find_free_workspace should be called."""
    monkeypatch.setattr("sys.argv", ["ham", "switch", "myrepo/feat"])
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.hyprland") as mock_hyprland,
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.windows_in_path", return_value=[]),
        patch("ham.cli.get_workspace_for_windows", return_value=None),
        patch("ham.cli.find_free_workspace", return_value=7) as mock_free,
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.list_worktrees.return_value = [("myrepo", "feat")]
        mock_git.resolve_worktree.return_value = (Path("/repo"), "feat")
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = True
        mock_git.branch_exists.return_value = True
        mock_hyprland.get_windows.return_value = []
        main()
    mock_free.assert_called_once()
    call_kwargs = mock_plan.call_args
    assert call_kwargs[1]["workspace_id"] is None
    assert call_kwargs[1]["free_workspace"] == 7


def test_switch_worktree_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve_worktree returns None, should raise SystemExit."""
    monkeypatch.setattr("sys.argv", ["ham", "switch", "myrepo/feat"])
    with (
        patch("ham.cli.git") as mock_git,
    ):
        mock_git.list_worktrees.return_value = [("myrepo", "feat")]
        mock_git.resolve_worktree.return_value = None
        with pytest.raises(SystemExit):
            main()


def test_fzf_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    """fzf returns non-zero, should raise SystemExit."""
    monkeypatch.setattr("sys.argv", ["ham", "switch"])
    fzf_result = CompletedProcess(args=["fzf"], returncode=130, stdout="", stderr="")
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.subprocess.run", return_value=fzf_result),
    ):
        mock_git.list_worktrees.return_value = [("myrepo", "feat")]
        with pytest.raises(SystemExit):
            main()
