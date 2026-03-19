import json
import logging
import os
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
    workspace_id: int = 0


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
            workspace_id=client["workspace"]["id"],
        )
        for client in clients
    ]


def get_workspace_for_windows(windows: list[HyprlandWindow]) -> int | None:
    """Given matched windows, return their workspace ID."""
    if not windows:
        return None
    return windows[0].workspace_id


def find_free_workspace() -> int:  # pragma: no cover
    """Return lowest unused workspace ID >= 1."""
    result = subprocess.run(
        ["hyprctl", "workspaces", "-j"],
        capture_output=True,
        text=True,
        check=True,
    )
    workspaces = json.loads(result.stdout)
    used = {ws["id"] for ws in workspaces}
    workspace_id = 1
    while workspace_id in used:
        workspace_id += 1
    return workspace_id


def _ancestor_pids() -> dict[int, int]:  # pragma: no cover
    """Walk up from our PID to init. Returns {pid: distance} where 0 is self."""
    pids = {}
    pid = os.getpid()
    distance = 0
    while pid > 1:
        pids[pid] = distance
        distance += 1
        try:
            stat = Path(f"/proc/{pid}/stat").read_text()
            ppid = int(stat.split(") ")[1].split()[1])
            pid = ppid
        except (OSError, ValueError, IndexError):
            break
    return pids


def windows_in_path(
    windows: list[HyprlandWindow], path: Path, own_last: bool = True
) -> list[HyprlandWindow]:
    resolved = path.resolve()
    ancestors = _ancestor_pids() if own_last else {}
    matched = []
    deferred = []
    for w in windows:
        if any(cwd.is_relative_to(resolved) for cwd in w.cwds):
            log.debug("match: %s %s pid=%d", w.address, w.class_name, w.pid)
            if own_last and w.pid in ancestors:
                log.debug(
                    "ancestor window (dist=%d), deferring: %s",
                    ancestors[w.pid],
                    w.address,
                )
                deferred.append(w)
            else:
                matched.append(w)
        else:
            log.debug(
                "skip: %s %s pid=%d cwds=%s", w.address, w.class_name, w.pid, w.cwds
            )
    deferred.sort(key=lambda w: ancestors.get(w.pid, 0), reverse=True)
    matched.extend(deferred)
    return matched
