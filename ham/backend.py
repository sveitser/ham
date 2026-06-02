import os
from dataclasses import replace
from pathlib import Path
from typing import Protocol

from ham import hyprland, tmux
from ham.actions import LaunchProcess, TmuxLayout
from ham.config import LayoutSpec
from ham.hyprland import HyprlandWindow
from ham.tmux import TmuxWindow


def _spec_or_default(spec: LayoutSpec | None, agent_continue: bool) -> LayoutSpec:
    """A passed spec is used as-is (agent_cmd already resolved); a missing spec
    falls back to defaults with --continue applied for backward compatibility."""
    if spec is not None:
        return spec
    base = LayoutSpec.defaults()
    if not agent_continue:
        return base
    return replace(base, agent_cmd=base.agent_cmd + ["--continue"])


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
        self,
        cwd: Path,
        workspace_id: str,
        agent_continue: bool,
        spec: LayoutSpec | None = None,
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
        self,
        cwd: Path,
        workspace_id: str,
        agent_continue: bool,
        spec: LayoutSpec | None = None,
    ) -> list[LaunchProcess]:
        spec = _spec_or_default(spec, agent_continue)
        direnv = ["direnv", "exec", str(cwd)] if spec.use_direnv else []
        term = spec.terminal
        return [
            LaunchProcess(
                cmd=[term.bin, term.cwd_flag, str(cwd)],
                workspace_id=workspace_id,
            ),
            LaunchProcess(
                cmd=direnv + spec.gui_editor + [str(cwd / spec.readme_file)],
                workspace_id=workspace_id,
            ),
            LaunchProcess(
                cmd=[term.bin, term.cwd_flag, str(cwd), term.exec_flag]
                + direnv
                + spec.agent_cmd,
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
        self,
        cwd: Path,
        workspace_id: str,
        agent_continue: bool,
        spec: LayoutSpec | None = None,
    ) -> list[TmuxLayout]:
        spec = _spec_or_default(spec, agent_continue)
        direnv = ["direnv", "exec", str(cwd)] if spec.use_direnv else []
        emacs_cmd = direnv + spec.headless_editor + [str(cwd)]
        agent_cmd = direnv + spec.agent_cmd
        return [
            TmuxLayout(
                session_name=workspace_id,
                cwd=cwd,
                emacs_cmd=emacs_cmd,
                agent_cmd=agent_cmd,
            )
        ]


def detect_backend() -> HyprlandBackend | TmuxBackend:
    return (
        HyprlandBackend()
        if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
        else TmuxBackend()
    )
