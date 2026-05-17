from pathlib import Path
from unittest.mock import patch

from ham.actions import LaunchProcess, TmuxLayout
from ham.backend import HyprlandBackend, TmuxBackend, detect_backend
from ham.hyprland import HyprlandWindow
from ham.tmux import TmuxWindow


def test_detect_backend_hyprland(monkeypatch) -> None:
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "abc123")
    assert isinstance(detect_backend(), HyprlandBackend)


def test_detect_backend_tmux(monkeypatch) -> None:
    monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)
    assert isinstance(detect_backend(), TmuxBackend)


def test_hyprland_backend_get_windows() -> None:
    b = HyprlandBackend()
    windows = [HyprlandWindow(window_id="0x1", pid=1, class_name="a", title="t")]
    with patch("ham.backend.hyprland.get_windows", return_value=windows):
        assert b.get_windows() == windows


def test_hyprland_backend_get_workspace_for_windows() -> None:
    b = HyprlandBackend()
    windows = [
        HyprlandWindow(
            window_id="0x1", pid=1, class_name="a", title="t", workspace_id=3
        )
    ]
    with patch("ham.backend.hyprland.get_workspace_for_windows", return_value="3"):
        assert b.get_workspace_for_windows(windows) == "3"


def test_hyprland_backend_find_free_workspace_str() -> None:
    b = HyprlandBackend()
    with patch("ham.backend.hyprland.find_free_workspace", return_value="7"):
        result = b.find_free_workspace()
    assert isinstance(result, str)
    assert result == "7"


def test_hyprland_backend_active_workspace_str() -> None:
    b = HyprlandBackend()
    with patch("ham.backend.hyprland.get_active_workspace", return_value=("3", 2)):
        ws_id, count = b.get_active_workspace()
    assert isinstance(ws_id, str)


def test_hyprland_backend_windows_in_path() -> None:
    b = HyprlandBackend()
    windows = [HyprlandWindow(window_id="0x1", pid=1, class_name="a", title="t")]
    with patch("ham.backend.hyprland.windows_in_path", return_value=windows):
        result = b.windows_in_path(windows, Path("/some/path"))
    assert result == windows


def test_tmux_backend_get_windows() -> None:
    b = TmuxBackend()
    windows = [
        TmuxWindow(session_name="s", window_index=0, pane_pid=1, pane_cwd=Path("/tmp"))
    ]
    with patch("ham.backend.tmux.get_windows", return_value=windows):
        assert b.get_windows() == windows


def test_tmux_backend_get_workspace_for_windows() -> None:
    b = TmuxBackend()
    windows = [
        TmuxWindow(
            session_name="myrepo-feat",
            window_index=0,
            pane_pid=1,
            pane_cwd=Path("/tmp"),
        )
    ]
    with patch("ham.backend.tmux.get_session_for_windows", return_value="myrepo-feat"):
        assert b.get_workspace_for_windows(windows) == "myrepo-feat"


def test_tmux_backend_find_free_delegates() -> None:
    b = TmuxBackend()
    with patch(
        "ham.backend.tmux.find_free_session", return_value="myrepo-feat"
    ) as mock:
        result = b.find_free_workspace("myrepo-feat")
    mock.assert_called_once_with("myrepo-feat")
    assert result == "myrepo-feat"


def test_tmux_backend_get_active_workspace() -> None:
    b = TmuxBackend()
    with patch("ham.backend.tmux.get_active_session", return_value=("myrepo-feat", 2)):
        result = b.get_active_workspace()
    assert result == ("myrepo-feat", 2)


def test_tmux_backend_windows_in_path() -> None:
    b = TmuxBackend()
    w = TmuxWindow(
        session_name="s", window_index=0, pane_pid=1, pane_cwd=Path("/tmp/wt")
    )
    with patch("ham.backend.tmux.windows_in_path", return_value=[w]):
        result = b.windows_in_path([w], Path("/tmp/wt"))
    assert result == [w]


def test_hyprland_backend_layout_actions() -> None:
    b = HyprlandBackend()
    actions = b.layout_actions(Path("/repo"), "5", False)
    assert len(actions) == 3
    assert all(isinstance(a, LaunchProcess) for a in actions)
    cmds = [a.cmd[0] for a in actions]
    assert "alacritty" in cmds
    assert "direnv" in cmds


def test_hyprland_backend_layout_actions_continue() -> None:
    b = HyprlandBackend()
    actions = b.layout_actions(Path("/repo"), "5", True)
    assert any("--continue" in a.cmd for a in actions)


def test_tmux_backend_layout_actions() -> None:
    b = TmuxBackend()
    actions = b.layout_actions(Path("/repo"), "myrepo-feat", False)
    assert len(actions) == 1
    assert isinstance(actions[0], TmuxLayout)
    assert actions[0].session_name == "myrepo-feat"
    assert "--continue" not in actions[0].claude_cmd


def test_tmux_backend_layout_actions_continue() -> None:
    b = TmuxBackend()
    actions = b.layout_actions(Path("/repo"), "myrepo-feat", True)
    assert "--continue" in actions[0].claude_cmd
