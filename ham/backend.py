import os
from pathlib import Path
from typing import Protocol

from ham import hyprland, tmux
from ham.actions import LaunchProcess, TmuxLayout
from ham.hyprland import HyprlandWindow
from ham.tmux import TmuxWindow


class Backend(Protocol):
    name: str

    def get_windows(self) -> list: ...
    def get_workspace_for_windows(self, windows: list) -> str | None: ...
    def find_free_workspace(self, hint: str = "") -> str: ...
    def get_active_workspace(self) -> tuple[str, int]: ...
    def windows_in_path(
        self, windows: list, path: Path, own_last: bool = True
    ) -> list: ...
    def layout_actions(
        self, cwd: Path, workspace_id: str, claude_continue: bool
    ) -> list: ...


class HyprlandBackend:
    name = "hyprland"

    def get_windows(self) -> list[HyprlandWindow]:
        return hyprland.get_windows()

    def get_workspace_for_windows(self, windows: list[HyprlandWindow]) -> str | None:
        return hyprland.get_workspace_for_windows(windows)

    def find_free_workspace(self, hint: str = "") -> str:
        return hyprland.find_free_workspace()

    def get_active_workspace(self) -> tuple[str, int]:
        return hyprland.get_active_workspace()

    def windows_in_path(
        self, windows: list[HyprlandWindow], path: Path, own_last: bool = True
    ) -> list[HyprlandWindow]:
        return hyprland.windows_in_path(windows, path, own_last)

    def layout_actions(
        self, cwd: Path, workspace_id: str, claude_continue: bool
    ) -> list[LaunchProcess]:
        direnv = ["direnv", "exec", str(cwd)]
        claude_cmd = direnv + ["claude"] + (["--continue"] if claude_continue else [])
        return [
            LaunchProcess(
                cmd=["alacritty", "--working-directory", str(cwd)],
                workspace_id=workspace_id,
            ),
            LaunchProcess(
                cmd=direnv + ["emacs", str(cwd / "README.md")],
                workspace_id=workspace_id,
            ),
            LaunchProcess(
                cmd=["alacritty", "--working-directory", str(cwd), "-e"] + claude_cmd,
                workspace_id=workspace_id,
            ),
        ]


class TmuxBackend:
    name = "tmux"

    def get_windows(self) -> list[TmuxWindow]:
        return tmux.get_windows()

    def get_workspace_for_windows(self, windows: list[TmuxWindow]) -> str | None:
        return tmux.get_session_for_windows(windows)

    def find_free_workspace(self, hint: str = "") -> str:
        return tmux.find_free_session(hint)

    def get_active_workspace(self) -> tuple[str, int]:
        return tmux.get_active_session()

    def windows_in_path(
        self, windows: list[TmuxWindow], path: Path, own_last: bool = True
    ) -> list[TmuxWindow]:
        return tmux.windows_in_path(windows, path, own_last)

    def layout_actions(
        self, cwd: Path, workspace_id: str, claude_continue: bool
    ) -> list[TmuxLayout]:
        direnv = ["direnv", "exec", str(cwd)]
        emacs_cmd = direnv + ["emacs", "-nw", str(cwd)]
        claude_cmd = direnv + ["claude"] + (["--continue"] if claude_continue else [])
        return [
            TmuxLayout(
                session_name=workspace_id,
                cwd=cwd,
                emacs_cmd=emacs_cmd,
                claude_cmd=claude_cmd,
            )
        ]


def detect_backend() -> HyprlandBackend | TmuxBackend:
    return (
        HyprlandBackend()
        if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
        else TmuxBackend()
    )
