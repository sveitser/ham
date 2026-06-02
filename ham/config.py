from __future__ import annotations

import os
import shlex
import sys
import tomllib
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

import platformdirs

CONFIG_PATH = platformdirs.user_config_path("ham") / "config.toml"


@dataclass(frozen=True)
class AgentRule:
    pattern: str
    command: list[str]


@dataclass(frozen=True)
class TerminalSpec:
    bin: str
    cwd_flag: str
    exec_flag: str


_ALACRITTY = TerminalSpec(
    bin="alacritty", cwd_flag="--working-directory", exec_flag="-e"
)

TERMINALS: dict[str, TerminalSpec] = {
    "alacritty": _ALACRITTY,
    "kitty": TerminalSpec(bin="kitty", cwd_flag="--directory", exec_flag="-e"),
}


@dataclass(frozen=True)
class Config:
    terminal: list[str] | None
    gui_editor: list[str]
    headless_editor: list[str]
    default_agent: list[str]
    agent_rules: tuple[AgentRule, ...]
    use_direnv: bool
    agent_continue_default: bool
    readme_file: str
    repo_dir: Path | None
    default_start_point: str | None

    @staticmethod
    def defaults() -> Config:
        return Config(
            terminal=None,
            gui_editor=["emacs"],
            headless_editor=["emacs", "-nw"],
            default_agent=["claude"],
            agent_rules=(),
            use_direnv=True,
            agent_continue_default=False,
            readme_file="README.md",
            repo_dir=None,
            default_start_point=None,
        )

    def resolve_agent(self, repo: Path, *, cont: bool) -> list[str]:
        matches = [r for r in self.agent_rules if fnmatch(str(repo), r.pattern)]
        if matches:
            best = max(matches, key=lambda r: (r.pattern.count("/"), len(r.pattern)))
            command = list(best.command)
        else:
            command = list(self.default_agent)
        return command + (["--continue"] if cont else [])


@dataclass(frozen=True)
class LayoutSpec:
    terminal: TerminalSpec
    gui_editor: list[str]
    headless_editor: list[str]
    agent_cmd: list[str]
    use_direnv: bool
    readme_file: str

    @staticmethod
    def defaults() -> LayoutSpec:
        return LayoutSpec(
            terminal=_ALACRITTY,
            gui_editor=["emacs"],
            headless_editor=["emacs", "-nw"],
            agent_cmd=["claude"],
            use_direnv=True,
            readme_file="README.md",
        )


def load_config(path: Path = CONFIG_PATH) -> Config:
    if not path.exists():
        return Config.defaults()
    with path.open("rb") as f:
        data = tomllib.load(f)
    return _parse(data)


def _parse(data: dict) -> Config:
    base = Config.defaults()
    terminal = base.terminal
    if "terminal" in data:
        terminal = shlex.split(data["terminal"])

    repo_dir = base.repo_dir
    if "repo_dir" in data:
        repo_dir = Path(os.path.expanduser(data["repo_dir"]))

    rules = tuple(
        AgentRule(
            pattern=os.path.expanduser(entry["pattern"]),
            command=shlex.split(entry["command"]),
        )
        for entry in data.get("agent", [])
    )

    return Config(
        terminal=terminal,
        gui_editor=shlex.split(data["gui_editor"])
        if "gui_editor" in data
        else base.gui_editor,
        headless_editor=shlex.split(data["headless_editor"])
        if "headless_editor" in data
        else base.headless_editor,
        default_agent=shlex.split(data["default_agent"])
        if "default_agent" in data
        else base.default_agent,
        agent_rules=rules,
        use_direnv=data["use_direnv"] if "use_direnv" in data else base.use_direnv,
        agent_continue_default=data["agent_continue_default"]
        if "agent_continue_default" in data
        else base.agent_continue_default,
        readme_file=data["readme_file"] if "readme_file" in data else base.readme_file,
        repo_dir=repo_dir,
        default_start_point=data["default_start_point"]
        if "default_start_point" in data
        else base.default_start_point,
    )


def init_config(path: Path = CONFIG_PATH) -> Path:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TEMPLATE)
    return path


def _normalize_terminal(name: str) -> str:
    return name.lower().removesuffix(".app")


def resolve_terminal(cfg: Config) -> TerminalSpec:
    if cfg.terminal is not None:
        bin_name = cfg.terminal[0]
        spec = TERMINALS.get(bin_name)
        if spec is not None:
            return spec
        return TerminalSpec(
            bin=bin_name, cwd_flag=_ALACRITTY.cwd_flag, exec_flag=_ALACRITTY.exec_flag
        )

    if sys.platform == "darwin":
        name = os.environ.get("TERM_PROGRAM", "")
    else:
        name = os.environ.get("TERM", "")
    return TERMINALS.get(_normalize_terminal(name), _ALACRITTY)


def build_layout_spec(cfg: Config, repo: Path, *, agent_continue: bool) -> LayoutSpec:
    return LayoutSpec(
        terminal=resolve_terminal(cfg),
        gui_editor=cfg.gui_editor,
        headless_editor=cfg.headless_editor,
        agent_cmd=cfg.resolve_agent(repo, cont=agent_continue),
        use_direnv=cfg.use_direnv,
        readme_file=cfg.readme_file,
    )


TEMPLATE = """# ham configuration. All keys optional; omitted keys use built-in defaults.

# Terminal emulator. If omitted, ham infers from $TERM_PROGRAM (macOS) / $TERM (Linux), else alacritty.
# Only used by the Hyprland backend; the tmux backend uses panes.
# terminal = "alacritty"

# Editors. gui_editor opens <worktree>/<readme_file>; headless_editor opens the worktree dir.
gui_editor = "emacs"
headless_editor = "emacs -nw"
readme_file = "README.md"

# Wrap launched commands in `direnv exec <cwd>`.
use_direnv = true

# Default agent command when no [[agent]] rule matches.
default_agent = "claude"

# Pass --continue to the agent by default when opening an existing worktree.
agent_continue_default = false

# Repo discovery root (overrides $HAM_REPO_DIR). Default: ~/r
# repo_dir = "~/r"

# Default start point for new branches. Default: origin/main
# default_start_point = "origin/main"

# Per-directory agent command. Patterns match the SOURCE REPO path (globs, ~ expanded).
# Most specific (deepest) matching pattern wins, regardless of order.
[[agent]]
pattern = "~/r/*"
command = "claude-sandbox --dangerously-skip-permissions"

[[agent]]
pattern = "~/r/EspressoSystems/*"
command = "claude-sandbox-work --dangerously-skip-permissions"
"""
