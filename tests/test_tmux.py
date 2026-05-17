from pathlib import Path
from ham.tmux import (
    TmuxWindow,
    find_free_session,
    get_session_for_windows,
    windows_in_path,
)


def _win(session: str, idx: int, cwd: str) -> TmuxWindow:
    return TmuxWindow(
        session_name=session, window_index=idx, pane_pid=1000 + idx, pane_cwd=Path(cwd)
    )


def test_get_session_for_windows_empty() -> None:
    assert get_session_for_windows([]) is None


def test_get_session_for_windows_returns_first() -> None:
    assert get_session_for_windows([_win("myrepo-feat", 0, "/tmp")]) == "myrepo-feat"


def test_windows_in_path_match() -> None:
    w = _win("s", 0, "/tmp/wt/myrepo/feat")
    assert windows_in_path([w], Path("/tmp/wt/myrepo/feat")) == [w]


def test_windows_in_path_no_match() -> None:
    w = _win("s", 0, "/other/path")
    assert windows_in_path([w], Path("/tmp/wt")) == []


def test_windows_in_path_subdirectory() -> None:
    w = _win("s", 0, "/tmp/wt/myrepo/feat/src")
    assert windows_in_path([w], Path("/tmp/wt/myrepo/feat")) == [w]


def test_find_free_session_returns_hint() -> None:
    assert find_free_session("myrepo-feat") == "myrepo-feat"
    assert find_free_session("") == ""


def test_tmux_window_id_property() -> None:
    w = _win("myrepo-feat", 2, "/tmp")
    assert w.window_id == "myrepo-feat:2"
