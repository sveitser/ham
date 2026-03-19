import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class HyprlandWindow:
    address: str
    pid: int
    class_name: str
    title: str
    cwds: list[Path] = field(default_factory=list)


def _resolve_cwds(pid: int) -> list[Path]:  # pragma: no cover
    """Resolve cwds for a pid and all its descendants."""
    cwds = []
    try:
        cwds.append(Path(f"/proc/{pid}/cwd").resolve())
    except (OSError, ValueError):
        pass
    try:
        children = Path(f"/proc/{pid}/task/{pid}/children").read_text().split()
        for child_str in children:
            cwds.extend(_resolve_cwds(int(child_str)))
    except (OSError, ValueError):
        pass
    return cwds


def get_windows() -> list[HyprlandWindow]:  # pragma: no cover
    result = subprocess.run(
        ["hyprctl", "clients", "-j"],
        capture_output=True,
        text=True,
        check=True,
    )
    clients = json.loads(result.stdout)
    return [
        HyprlandWindow(
            address=client["address"],
            pid=client["pid"],
            class_name=client["class"],
            title=client["title"],
            cwds=_resolve_cwds(client["pid"]),
        )
        for client in clients
    ]


def windows_in_path(windows: list[HyprlandWindow], path: Path) -> list[HyprlandWindow]:
    resolved = path.resolve()
    matched = []
    for w in windows:
        if any(cwd.is_relative_to(resolved) for cwd in w.cwds):
            log.debug("match: %s %s pid=%d", w.address, w.class_name, w.pid)
            matched.append(w)
        else:
            log.debug(
                "skip: %s %s pid=%d cwds=%s", w.address, w.class_name, w.pid, w.cwds
            )
    return matched
