from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest

from ham.cli import _version_str, main
from ham.git import WorktreeStatus
from ham.hyprland import HyprlandWindow


def _wt_status(
    repo_name: str, branch: str, modified: bool = False, untracked: bool = False
):
    return WorktreeStatus(
        repo=Path(f"/r/{repo_name}"),
        branch=branch,
        wt_path=Path(f"/wt/{repo_name}/{branch}"),
        has_modified=modified,
        has_untracked=untracked,
    )


def _mock_backend(
    windows=None,
    workspace_id=None,
    active_workspace=("1", 0),
    free_workspace="5",
):
    b = MagicMock()
    b.name = "hyprland"
    b.get_windows.return_value = windows or []
    b.get_workspace_for_windows.return_value = workspace_id
    b.get_active_workspace.return_value = active_workspace
    b.find_free_workspace.return_value = free_workspace
    b.windows_in_path.return_value = (
        [w for w in (windows or [])] if workspace_id is not None else []
    )
    return b


FAKE_WT = Path("/fake/wt")


def test_open_parses_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open", "/some/path", "my-branch"])
    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute") as mock_exec,
    ):
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = False
        mock_git.branch_exists.return_value = False
        main()
    mock_plan.assert_called_once()
    mock_exec.assert_called_once_with([], "hyprland")


def test_open_selection_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open", "myrepo/feat"])
    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute") as mock_exec,
    ):
        mock_git.resolve_worktree.return_value = (Path("/repo"), "feat")
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = False
        mock_git.branch_exists.return_value = False
        main()
    mock_git.resolve_worktree.assert_called_once_with("myrepo/feat")
    mock_plan.assert_called_once()
    mock_exec.assert_called_once_with([], "hyprland")


def test_open_selection_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open", "nope/nope"])
    with patch("ham.cli.git") as mock_git:
        mock_git.resolve_worktree.return_value = None
        mock_git.resolve_repo.side_effect = ValueError("no repo found with name 'nope'")
        with pytest.raises(SystemExit):
            main()


def test_open_no_args_fzf_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open"])
    fzf_result = CompletedProcess(args=["fzf"], returncode=130, stdout="", stderr="")
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.subprocess.run", return_value=fzf_result),
    ):
        mock_git.discover_repos.return_value = [Path("/r/org/myrepo")]
        with pytest.raises(SystemExit):
            main()


def test_open_selection_no_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open", "something"])
    with patch("ham.cli.git") as mock_git:
        mock_git.resolve_worktree.return_value = None
        with pytest.raises(SystemExit):
            main()


def test_open_fetches_when_worktree_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open", "/some/path", "my-branch"])
    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = False
        mock_git.branch_exists.return_value = False
        mock_git.remote_branch_exists.return_value = True
        main()
    mock_git.fetch_origin.assert_called_once()
    assert mock_plan.call_args[1]["remote_branch_exists"] is True


def test_open_passes_start_point_from_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["ham", "open", "/some/path", "my-branch", "--from", "origin/dev"],
    )
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.hyprland") as mock_hyprland,
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.windows_in_path", return_value=[]),
        patch("ham.cli.get_workspace_for_windows", return_value=None),
        patch("ham.cli.get_active_workspace", return_value=(1, 5)),
        patch("ham.cli.find_free_workspace", return_value=5),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = False
        mock_git.branch_exists.return_value = False
        mock_git.remote_branch_exists.return_value = False
        mock_hyprland.get_windows.return_value = []
        main()
    assert mock_plan.call_args[1]["start_point"] == "origin/dev"


def test_open_default_start_point_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open", "/some/path", "my-branch"])
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.hyprland") as mock_hyprland,
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.windows_in_path", return_value=[]),
        patch("ham.cli.get_workspace_for_windows", return_value=None),
        patch("ham.cli.get_active_workspace", return_value=(1, 5)),
        patch("ham.cli.find_free_workspace", return_value=5),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = False
        mock_git.branch_exists.return_value = False
        mock_git.remote_branch_exists.return_value = False
        mock_hyprland.get_windows.return_value = []
        main()
    assert mock_plan.call_args[1]["start_point"] is None


def test_open_no_fetch_when_not_a_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open", "/some/path", "my-branch"])
    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_switch", side_effect=ValueError("not a git repo")),
        patch("ham.cli.execute"),
    ):
        mock_git.is_git_repo.return_value = False
        mock_git.worktree_exists.return_value = False
        mock_git.branch_exists.return_value = False
        with pytest.raises(ValueError):
            main()
    mock_git.fetch_origin.assert_not_called()


def test_open_no_fetch_when_worktree_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open", "/some/path", "my-branch"])
    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_switch", return_value=[]),
        patch("ham.cli.execute"),
    ):
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = True
        mock_git.branch_exists.return_value = True
        main()
    mock_git.fetch_origin.assert_not_called()


def test_open_smart_resolve(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open", "myrepo/new-feat"])
    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.resolve_worktree.return_value = None
        mock_git.resolve_repo.return_value = Path("/r/org/myrepo")
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = False
        mock_git.branch_exists.return_value = False
        main()
    mock_git.resolve_repo.assert_called_once_with("myrepo")
    mock_plan.assert_called_once()


def test_open_interactive_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open"])
    repo_fzf = CompletedProcess(
        args=["fzf"], returncode=0, stdout="/r/org/myrepo\n", stderr=""
    )
    branch_fzf = CompletedProcess(
        args=["fzf"], returncode=0, stdout="main\nmain\n", stderr=""
    )
    call_count = {"n": 0}

    def mock_fzf(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return repo_fzf
        return branch_fzf

    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.subprocess.run", side_effect=mock_fzf),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.discover_repos.return_value = [Path("/r/org/myrepo")]
        mock_git.list_branches.return_value = ["main", "dev"]
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = False
        mock_git.branch_exists.return_value = False
        main()
    mock_plan.assert_called_once()


def test_open_interactive_new_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open"])
    repo_fzf = CompletedProcess(
        args=["fzf"], returncode=0, stdout="/r/org/myrepo\n", stderr=""
    )
    branch_fzf = CompletedProcess(
        args=["fzf"], returncode=1, stdout="new-feat\n", stderr=""
    )
    call_count = {"n": 0}

    def mock_fzf(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return repo_fzf
        return branch_fzf

    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.subprocess.run", side_effect=mock_fzf),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.discover_repos.return_value = [Path("/r/org/myrepo")]
        mock_git.list_branches.return_value = ["main", "dev"]
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = False
        mock_git.branch_exists.return_value = False
        main()
    mock_plan.assert_called_once()


def test_close_parses_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "close", "/some/path", "my-branch"])
    backend = _mock_backend()
    with (
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.plan_close", return_value=[]) as mock_plan,
        patch("ham.cli.execute") as mock_exec,
    ):
        main()
    mock_plan.assert_called_once()
    mock_exec.assert_called_once_with([], "hyprland")


def test_delete_parses_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "delete", "/some/path", "my-branch"])
    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_delete", return_value=[]) as mock_plan,
        patch("ham.cli.execute") as mock_exec,
    ):
        mock_git.worktree_exists.return_value = True
        mock_git.is_dirty.return_value = (False, "")
        main()
    mock_plan.assert_called_once()
    mock_exec.assert_called_once_with([], "hyprland")


def test_close_no_args_resolves_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "close"])
    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.plan_close", return_value=[]) as mock_plan,
        patch("ham.cli.execute") as mock_exec,
    ):
        mock_git.resolve_from_cwd.return_value = (Path("/repo"), "feat")
        main()
    mock_plan.assert_called_once()
    mock_exec.assert_called_once_with([], "hyprland")


def test_close_no_args_not_in_worktree(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "close"])
    with patch("ham.cli.git") as mock_git:
        mock_git.resolve_from_cwd.return_value = None
        mock_git.git_root_from_cwd.return_value = None
        with pytest.raises(SystemExit):
            main()


def test_close_no_args_falls_back_to_git_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "close"])
    backend = _mock_backend()
    repo_path = Path("/r/myrepo")
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.plan_close", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.resolve_from_cwd.return_value = None
        mock_git.git_root_from_cwd.return_value = repo_path
        main()
    mock_plan.assert_called_once_with(backend.windows_in_path.return_value)


def test_delete_no_args_resolves_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "delete"])
    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_delete", return_value=[]) as mock_plan,
        patch("ham.cli.execute") as mock_exec,
    ):
        mock_git.resolve_from_cwd.return_value = (Path("/repo"), "feat")
        mock_git.worktree_exists.return_value = True
        mock_git.is_dirty.return_value = (False, "")
        main()
    mock_plan.assert_called_once()
    mock_exec.assert_called_once_with([], "hyprland")


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
    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute") as mock_exec,
    ):
        mock_git.list_worktrees.return_value = [("myrepo", "feat")]
        mock_git.resolve_worktree.return_value = (Path("/repo"), "feat")
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = True
        mock_git.branch_exists.return_value = True
        main()
    mock_plan.assert_called_once()
    mock_exec.assert_called_once_with([], "hyprland")


def test_switch_no_query_fzf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "switch"])
    fzf_result = CompletedProcess(
        args=["fzf"], returncode=0, stdout="wt: myrepo/feat\tM\n", stderr=""
    )
    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.subprocess.run", return_value=fzf_result) as mock_run,
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.list_worktree_status.return_value = [
            _wt_status("myrepo", "feat", True)
        ]
        mock_git.discover_repos.return_value = []
        mock_git.resolve_worktree.return_value = (Path("/repo"), "feat")
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = True
        mock_git.branch_exists.return_value = True
        main()
    cmd = mock_run.call_args.args[0]
    assert cmd[0] == "fzf"
    assert "--bind" in cmd
    bind = cmd[cmd.index("--bind") + 1]
    assert bind.startswith("ctrl-d:")
    assert mock_run.call_args.kwargs["input"] == "wt: myrepo/feat\tM"
    mock_plan.assert_called_once()


def test_switch_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "switch", "nope/nope"])
    with patch("ham.cli.git") as mock_git:
        mock_git.resolve_worktree.return_value = None
        with pytest.raises(SystemExit):
            main()


def test_switch_no_worktrees(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "switch", "anything"])
    with patch("ham.cli.git") as mock_git:
        mock_git.resolve_worktree.return_value = None
        with pytest.raises(SystemExit):
            main()


def test_rofi_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "rofi"])
    rofi_result = CompletedProcess(
        args=["rofi"], returncode=0, stdout="wt: myrepo/feat\t\n", stderr=""
    )
    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.subprocess.run", return_value=rofi_result) as mock_run,
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.list_worktree_status.return_value = [_wt_status("myrepo", "feat")]
        mock_git.discover_repos.return_value = []
        mock_git.resolve_worktree.return_value = (Path("/repo"), "feat")
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = True
        mock_git.branch_exists.return_value = True
        main()
    mock_run.assert_called_once_with(
        ["rofi", "-dmenu", "-p", "ham", "-i"],
        input="wt: myrepo/feat\t",
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
        mock_git.list_worktree_status.return_value = [_wt_status("myrepo", "feat")]
        mock_git.discover_repos.return_value = []
        with pytest.raises(SystemExit):
            main()


def test_rofi_repo_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Selecting 'repo: foo' switches to the repo path directly, no worktree."""
    monkeypatch.setattr("sys.argv", ["ham", "rofi"])
    rofi_result = CompletedProcess(
        args=["rofi"], returncode=0, stdout="repo: myrepo\n", stderr=""
    )
    backend = _mock_backend(active_workspace=("1", 0))
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.subprocess.run", return_value=rofi_result),
        patch("ham.cli.plan_switch_repo", return_value=[]) as mock_plan,
        patch("ham.cli.plan_switch") as mock_plan_wt,
        patch("ham.cli.execute"),
    ):
        mock_git.list_worktree_status.return_value = []
        mock_git.discover_repos.return_value = [Path("/r/org/myrepo")]
        mock_git.resolve_repo.return_value = Path("/r/org/myrepo")
        main()
    mock_git.resolve_repo.assert_called_once_with("myrepo")
    mock_plan.assert_called_once()
    mock_plan_wt.assert_not_called()
    assert mock_plan.call_args[0][0] == Path("/r/org/myrepo")


def test_switch_repo_query(monkeypatch: pytest.MonkeyPatch) -> None:
    """ham switch 'repo: foo' resolves to repo path, uses plan_switch_repo."""
    monkeypatch.setattr("sys.argv", ["ham", "switch", "repo: myrepo"])
    backend = _mock_backend(active_workspace=("1", 0))
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.plan_switch_repo", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.resolve_repo.return_value = Path("/r/org/myrepo")
        main()
    mock_git.resolve_repo.assert_called_once_with("myrepo")
    mock_plan.assert_called_once()


def test_switch_repo_ambiguous_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve_repo ValueError must surface as SystemExit."""
    monkeypatch.setattr("sys.argv", ["ham", "switch", "repo: dup"])
    with patch("ham.cli.git") as mock_git:
        mock_git.resolve_repo.side_effect = ValueError("multiple repos found")
        with pytest.raises(SystemExit):
            main()


def test_switch_no_entries_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """No worktrees and no repos: fzf/rofi gets nothing to pick from."""
    monkeypatch.setattr("sys.argv", ["ham", "switch"])
    with patch("ham.cli.git") as mock_git:
        mock_git.list_worktree_status.return_value = []
        mock_git.discover_repos.return_value = []
        with pytest.raises(SystemExit):
            main()


def test_switch_repo_existing_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Existing windows in repo path: switch to their workspace, no launch."""
    monkeypatch.setattr("sys.argv", ["ham", "switch", "repo: myrepo"])
    window = HyprlandWindow(
        window_id="0x1", pid=1, class_name="alacritty", title="t", workspace_id=4
    )
    backend = _mock_backend(windows=[window], workspace_id="4")
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.plan_switch_repo", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.resolve_repo.return_value = Path("/r/org/myrepo")
        main()
    backend.find_free_workspace.assert_not_called()
    call_kwargs = mock_plan.call_args
    assert call_kwargs[1]["workspace_id"] == "4"
    assert call_kwargs[1]["free_workspace"] == "0"


def test_switch_existing_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    """workspace_id is not None, find_free_workspace should not be called."""
    monkeypatch.setattr("sys.argv", ["ham", "switch", "myrepo/feat"])
    window = HyprlandWindow(
        window_id="0x1", pid=1, class_name="alacritty", title="t", workspace_id=3
    )
    backend = _mock_backend(windows=[window], workspace_id="3")
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.list_worktrees.return_value = [("myrepo", "feat")]
        mock_git.resolve_worktree.return_value = (Path("/repo"), "feat")
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = True
        mock_git.branch_exists.return_value = True
        main()
    backend.find_free_workspace.assert_not_called()
    mock_plan.assert_called_once()
    call_kwargs = mock_plan.call_args
    assert call_kwargs[1]["workspace_id"] == "3"
    assert call_kwargs[1]["free_workspace"] == "0"


def test_switch_new_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    """No matched windows and active workspace crowded: use free workspace."""
    monkeypatch.setattr("sys.argv", ["ham", "switch", "myrepo/feat"])
    backend = _mock_backend(active_workspace=("2", 3), free_workspace="7")
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.list_worktrees.return_value = [("myrepo", "feat")]
        mock_git.resolve_worktree.return_value = (Path("/repo"), "feat")
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = True
        mock_git.branch_exists.return_value = True
        main()
    backend.find_free_workspace.assert_called_once()
    call_kwargs = mock_plan.call_args
    assert call_kwargs[1]["workspace_id"] is None
    assert call_kwargs[1]["free_workspace"] == "7"


def test_switch_reuses_active_when_single_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Active workspace with <=1 window is reused instead of a free one."""
    monkeypatch.setattr("sys.argv", ["ham", "switch", "myrepo/feat"])
    backend = _mock_backend(active_workspace=("4", 1))
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.list_worktrees.return_value = [("myrepo", "feat")]
        mock_git.resolve_worktree.return_value = (Path("/repo"), "feat")
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = True
        mock_git.branch_exists.return_value = True
        main()
    backend.find_free_workspace.assert_not_called()
    call_kwargs = mock_plan.call_args
    assert call_kwargs[1]["workspace_id"] is None
    assert call_kwargs[1]["free_workspace"] == "4"


def test_switch_reuses_active_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty active workspace is reused."""
    monkeypatch.setattr("sys.argv", ["ham", "switch", "myrepo/feat"])
    backend = _mock_backend(active_workspace=("9", 0))
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.list_worktrees.return_value = [("myrepo", "feat")]
        mock_git.resolve_worktree.return_value = (Path("/repo"), "feat")
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = True
        mock_git.branch_exists.return_value = True
        main()
    backend.find_free_workspace.assert_not_called()
    call_kwargs = mock_plan.call_args
    assert call_kwargs[1]["free_workspace"] == "9"


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


def test_close_target_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "close", "myrepo/feat"])
    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_close", return_value=[]) as mock_plan,
        patch("ham.cli.execute") as mock_exec,
    ):
        mock_git.resolve_worktree.return_value = (Path("/repo"), "feat")
        main()
    mock_plan.assert_called_once()
    mock_exec.assert_called_once_with([], "hyprland")


def test_close_target_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "close", "nope/nope"])
    with patch("ham.cli.git") as mock_git:
        mock_git.resolve_worktree.return_value = None
        with pytest.raises(SystemExit):
            main()


def test_delete_target_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "delete", "myrepo/feat"])
    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_delete", return_value=[]) as mock_plan,
        patch("ham.cli.execute") as mock_exec,
    ):
        mock_git.resolve_worktree.return_value = (Path("/repo"), "feat")
        mock_git.worktree_exists.return_value = True
        mock_git.is_dirty.return_value = (False, "")
        main()
    mock_plan.assert_called_once()
    mock_exec.assert_called_once_with([], "hyprland")


def test_delete_target_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "delete", "nope/nope"])
    with patch("ham.cli.git") as mock_git:
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


def test_default_no_command_runs_picker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham"])
    fzf_result = CompletedProcess(
        args=["fzf"], returncode=0, stdout="wt: a/main\t\n", stderr=""
    )
    backend = _mock_backend(active_workspace=("1", 0))
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.subprocess.run", return_value=fzf_result) as mock_run,
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.list_worktree_status.return_value = [_wt_status("a", "main")]
        mock_git.discover_repos.return_value = []
        mock_git.resolve_worktree.return_value = (Path("/r/a"), "main")
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = True
        mock_git.branch_exists.return_value = True
        main()
    cmd = mock_run.call_args.args[0]
    assert cmd[0] == "fzf"
    bind = cmd[cmd.index("--bind") + 1]
    assert bind.startswith("ctrl-d:")
    assert "delete {1}" in bind and "_entries" in bind
    mock_plan.assert_called_once()


def test_entries_subcommand_prints(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "_entries"])
    with patch("ham.cli.git") as mock_git:
        mock_git.list_worktree_status.return_value = [
            _wt_status("a", "main"),
            _wt_status("b", "feat", modified=True, untracked=True),
        ]
        mock_git.discover_repos.return_value = [Path("/r/org/c")]
        main()
    assert capsys.readouterr().out == "wt: a/main\t\nwt: b/feat\tM?\nrepo: c\t\n"


def test_delete_strips_wt_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    """ham delete 'wt: foo/bar' resolves bar via foo (prefix stripped)."""
    monkeypatch.setattr("sys.argv", ["ham", "delete", "wt: myrepo/feat"])
    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_delete", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.resolve_worktree.return_value = (Path("/r/myrepo"), "feat")
        mock_git.is_dirty.return_value = (False, "")
        mock_git.worktree_exists.return_value = True
        main()
    mock_git.resolve_worktree.assert_called_once_with("myrepo/feat")
    mock_plan.assert_called_once()


def test_delete_repo_prefix_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "delete", "repo: myrepo"])
    with patch("ham.cli.git"):
        with pytest.raises(SystemExit):
            main()
    assert "cannot delete a repo entry" in capsys.readouterr().err


def test_close_repo_prefix_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "close", "repo: myrepo"])
    backend = _mock_backend()
    repo_path = Path("/r/myrepo")
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.plan_close", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.resolve_repo.return_value = repo_path
        main()
    mock_git.resolve_repo.assert_called_once_with("myrepo")
    mock_plan.assert_called_once_with(backend.windows_in_path.return_value)


def test_close_strips_wt_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "close", "wt: myrepo/feat"])
    backend = _mock_backend()
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_close", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.resolve_worktree.return_value = (Path("/r/myrepo"), "feat")
        main()
    mock_git.resolve_worktree.assert_called_once_with("myrepo/feat")
    mock_plan.assert_called_once()


def test_pick_repo_no_repos_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open"])
    with patch("ham.cli.git") as mock_git:
        mock_git.discover_repos.return_value = []
        with pytest.raises(SystemExit):
            main()


def test_pick_branch_fzf_abort(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "open"])
    repo_fzf = CompletedProcess(
        args=["fzf"], returncode=0, stdout="/r/org/myrepo\n", stderr=""
    )
    branch_fzf = CompletedProcess(args=["fzf"], returncode=130, stdout="", stderr="")
    call_count = {"n": 0}

    def mock_fzf(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return repo_fzf
        return branch_fzf

    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.subprocess.run", side_effect=mock_fzf),
    ):
        mock_git.discover_repos.return_value = [Path("/r/org/myrepo")]
        mock_git.list_branches.return_value = []
        with pytest.raises(SystemExit):
            main()


def test_target_workspace_tmux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "switch", "myrepo/feat"])
    backend = _mock_backend(free_workspace="myrepo-feat")
    backend.name = "tmux"
    with (
        patch("ham.cli.git") as mock_git,
        patch("ham.cli.detect_backend", return_value=backend),
        patch("ham.cli.worktree_path", return_value=FAKE_WT),
        patch("ham.cli.plan_switch", return_value=[]) as mock_plan,
        patch("ham.cli.execute"),
    ):
        mock_git.resolve_worktree.return_value = (Path("/repo"), "feat")
        mock_git.is_git_repo.return_value = True
        mock_git.worktree_exists.return_value = True
        mock_git.branch_exists.return_value = True
        main()
    mock_plan.assert_called_once()
    call_kwargs = mock_plan.call_args
    assert call_kwargs[1]["backend"] is backend


def test_version_str_dev_uses_git(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ham.cli.GIT_REV", "@GIT_REV@")
    monkeypatch.setattr("ham.cli.GIT_DATE", "@GIT_DATE@")
    with patch("ham.cli.subprocess.run") as mock_run:
        mock_run.side_effect = [
            CompletedProcess([], 0, stdout="abc1234\n"),
            CompletedProcess([], 0, stdout="1747520655\n"),
        ]
        result = _version_str()
    from datetime import datetime, timezone

    epoch = 1747520655
    expected_ts = datetime.fromtimestamp(epoch, tz=timezone.utc).strftime(
        "%Y-%m-%d_%H_%M_%S"
    )
    assert result == f"0.1.0+abc1234.{expected_ts}"


def test_version_str_dev_git_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ham.cli.GIT_REV", "@GIT_REV@")
    monkeypatch.setattr("ham.cli.GIT_DATE", "@GIT_DATE@")
    with patch("ham.cli.subprocess.run", side_effect=Exception("no git")):
        result = _version_str()
    assert result == "0.1.0+dev.unknown"


def test_version_str_baked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ham.cli.GIT_REV", "deadbeef")
    monkeypatch.setattr("ham.cli.GIT_DATE", "2026-05-17_22_00_00")
    assert _version_str() == "0.1.0+deadbeef.2026-05-17_22_00_00"


def test_version_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["ham", "version"])
    monkeypatch.setattr("ham.cli.GIT_REV", "deadbeef")
    monkeypatch.setattr("ham.cli.GIT_DATE", "2026-05-17_22_00_00")
    main()
    assert capsys.readouterr().out.strip() == "0.1.0+deadbeef.2026-05-17_22_00_00"
