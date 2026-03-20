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


@dataclass
class GitWorktreeRemove(Action):
    repo: Path
    worktree_path: Path


@dataclass
class SetupDirenv(Action):
    cwd: Path


@dataclass
class LaunchProcess(Action):
    cmd: list[str]
    cwd: Path


@dataclass
class CloseWindow(Action):
    address: str


@dataclass
class ExecProcess(Action):
    cmd: list[str]
    cwd: Path
    fallback_cmd: list[str] | None = None


@dataclass
class PromptConfirmation(Action):
    message: str


@dataclass
class SwitchWorkspace(Action):
    workspace_id: int
