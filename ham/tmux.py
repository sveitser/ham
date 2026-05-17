import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from subprocess import CalledProcessError

log = logging.getLogger(__name__)


@dataclass
class TmuxWindow:
    session_name: str
    window_index: int
    pane_pid: int
    pane_cwd: Path

    @property
    def window_id(self) -> str:
        return f"{self.session_name}:{self.window_index}"


def get_session_for_windows(windows: list[TmuxWindow]) -> str | None:
    if not windows:
        return None
    return windows[0].session_name


def find_free_session(hint: str) -> str:
    return hint


def windows_in_path(windows: list[TmuxWindow], path: Path) -> list[TmuxWindow]:
    resolved = path.resolve()
    return [w for w in windows if w.pane_cwd.resolve().is_relative_to(resolved)]


def get_windows() -> list[TmuxWindow]:  # pragma: no cover
    try:
        result = subprocess.run(
            [
                "tmux",
                "list-panes",
                "-a",
                "-F",
                "#{session_name} #{window_index} #{pane_pid} #{pane_current_path}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except CalledProcessError:
        return []
    windows = []
    for line in result.stdout.splitlines():
        parts = line.split(" ", 3)
        if len(parts) != 4:
            continue
        session_name, window_index, pane_pid, pane_cwd = parts
        windows.append(
            TmuxWindow(
                session_name=session_name,
                window_index=int(window_index),
                pane_pid=int(pane_pid),
                pane_cwd=Path(pane_cwd),
            )
        )
    return windows


def get_active_session() -> tuple[str, int]:  # pragma: no cover
    result = subprocess.run(
        ["tmux", "display-message", "-p", "#{session_name} #{session_windows}"],
        capture_output=True,
        text=True,
        check=True,
    )
    parts = result.stdout.strip().split()
    return parts[0], int(parts[1])
