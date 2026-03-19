import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HyprlandWindow:
    address: str
    pid: int
    class_name: str
    title: str
    cwd: Path | None


def get_windows() -> list[HyprlandWindow]:  # pragma: no cover
    result = subprocess.run(
        ["hyprctl", "clients", "-j"],
        capture_output=True,
        text=True,
        check=True,
    )
    clients = json.loads(result.stdout)
    windows = []
    for client in clients:
        pid = client["pid"]
        cwd = None
        try:
            cwd = Path(f"/proc/{pid}/cwd").resolve()
        except (OSError, ValueError):
            pass
        windows.append(
            HyprlandWindow(
                address=client["address"],
                pid=pid,
                class_name=client["class"],
                title=client["title"],
                cwd=cwd,
            )
        )
    return windows


def windows_in_path(windows: list[HyprlandWindow], path: Path) -> list[HyprlandWindow]:
    resolved = path.resolve()
    return [w for w in windows if w.cwd is not None and w.cwd.is_relative_to(resolved)]
