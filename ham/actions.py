from dataclasses import dataclass
from pathlib import Path


@dataclass
class Action:
    pass


@dataclass
class GitWorktreeAdd(Action):
    repo: Path
    worktree_path: Path
    branch: str
    create_branch: bool
    start_point: str | None = None


@dataclass
class GitWorktreeRemove(Action):
    repo: Path
    worktree_path: Path
    force: bool = False


@dataclass
class SetupDirenv(Action):
    cwd: Path


@dataclass
class LaunchProcess(Action):
    cmd: list[str]
    workspace_id: str
    cwd: Path | None = None


@dataclass
class CloseWindow(Action):
    window_id: str


@dataclass
class PromptConfirmation(Action):
    message: str


@dataclass
class SwitchWorkspace(Action):
    workspace_id: str


@dataclass
class TmuxLayout(Action):
    session_name: str
    cwd: Path
    emacs_cmd: list[str]
    claude_cmd: list[str]
