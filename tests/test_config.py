import tomllib
from pathlib import Path

import pytest

from ham import config
from ham.config import (
    TEMPLATE,
    AgentRule,
    Config,
    LayoutSpec,
    TerminalSpec,
    _parse,
    build_layout_spec,
    init_config,
    load_config,
    resolve_terminal,
)


def test_config_missing_defaults_ok(tmp_path: Path) -> None:
    """REQ:config-missing-defaults: absent file loads built-in defaults."""
    cfg = load_config(tmp_path / "nope.toml")
    assert cfg == Config.defaults()


def test_config_partial_override_ok() -> None:
    """REQ:config-partial-override: present keys override, omitted keep defaults."""
    cfg = _parse({"gui_editor": "nvim", "use_direnv": False})
    assert cfg.gui_editor == ["nvim"]
    assert cfg.use_direnv is False
    assert cfg.headless_editor == ["emacs", "-nw"]
    assert cfg.default_agent == ["claude"]


def test_config_agent_deepest_wins_ok() -> None:
    """REQ:config-agent-deepest-wins: most-specific rule selects the command."""
    cfg = _parse(
        {
            "agent": [
                {"pattern": "/r/*", "command": "shallow"},
                {"pattern": "/r/org/*", "command": "deep"},
            ]
        }
    )
    assert cfg.resolve_agent(Path("/r/org/repo"), cont=False) == ["deep"]


def test_config_agent_deepest_wins_order_independent() -> None:
    cfg = _parse(
        {
            "agent": [
                {"pattern": "/r/org/*", "command": "deep"},
                {"pattern": "/r/*", "command": "shallow"},
            ]
        }
    )
    assert cfg.resolve_agent(Path("/r/org/repo"), cont=False) == ["deep"]


def test_config_agent_default_ok() -> None:
    """REQ:config-agent-default: no matching rule falls back to default_agent."""
    cfg = _parse({"agent": [{"pattern": "/other/*", "command": "x"}]})
    assert cfg.resolve_agent(Path("/r/repo"), cont=False) == ["claude"]


def test_config_agent_continue_appended_ok() -> None:
    """EDGE:config-agent-continue-appended: cont=True appends --continue."""
    cfg = _parse({"agent": [{"pattern": "/r/*", "command": "agent --flag"}]})
    assert cfg.resolve_agent(Path("/r/repo"), cont=True) == [
        "agent",
        "--flag",
        "--continue",
    ]


def test_config_tilde_expansion_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """EDGE:config-tilde-expansion: ~ expands in patterns and repo_dir."""
    monkeypatch.setenv("HOME", "/home/tester")
    cfg = _parse(
        {
            "repo_dir": "~/r",
            "agent": [{"pattern": "~/r/*", "command": "x"}],
        }
    )
    assert cfg.repo_dir == Path("/home/tester/r")
    assert cfg.agent_rules[0].pattern == "/home/tester/r/*"
    assert cfg.resolve_agent(Path("/home/tester/r/repo"), cont=False) == ["x"]


def test_config_terminal_infer_config_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ:config-terminal-infer: explicit config terminal wins."""
    monkeypatch.setattr(config.sys, "platform", "linux")
    monkeypatch.setenv("TERM", "alacritty")
    cfg = _parse({"terminal": "kitty"})
    assert resolve_terminal(cfg) == config.TERMINALS["kitty"]


def test_config_terminal_infer_env_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.sys, "platform", "linux")
    monkeypatch.setenv("TERM", "kitty")
    assert resolve_terminal(Config.defaults()) == config.TERMINALS["kitty"]


def test_config_terminal_infer_env_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.sys, "platform", "darwin")
    monkeypatch.setenv("TERM_PROGRAM", "iTerm.app")
    monkeypatch.delenv("TERM", raising=False)
    assert resolve_terminal(Config.defaults()) == config.TERMINALS.get(
        "iterm", config._ALACRITTY
    )


def test_config_terminal_infer_fallback_alacritty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config.sys, "platform", "linux")
    monkeypatch.setenv("TERM", "xterm-256color")
    assert resolve_terminal(Config.defaults()) == config._ALACRITTY


def test_config_unknown_terminal_ok() -> None:
    """EDGE:config-unknown-terminal: unknown bin falls back to alacritty flags."""
    cfg = _parse({"terminal": "weird-term"})
    spec = resolve_terminal(cfg)
    assert spec.bin == "weird-term"
    assert spec.cwd_flag == config._ALACRITTY.cwd_flag
    assert spec.exec_flag == config._ALACRITTY.exec_flag


def test_config_no_direnv_ok() -> None:
    """EDGE:config-no-direnv: use_direnv=false carried into LayoutSpec."""
    cfg = _parse({"use_direnv": False})
    spec = build_layout_spec(cfg, Path("/r/repo"), agent_continue=False)
    assert spec.use_direnv is False


def test_init_writes_config_ok(tmp_path: Path) -> None:
    """REQ:init-writes-config: writes valid TOML to the path."""
    path = tmp_path / "sub" / "config.toml"
    result = init_config(path)
    assert result == path
    assert path.exists()
    tomllib.loads(path.read_text())


def test_init_refuses_existing_fails(tmp_path: Path) -> None:
    """REQ:init-refuses-existing: errors when config exists."""
    path = tmp_path / "config.toml"
    path.write_text("")
    with pytest.raises(FileExistsError):
        init_config(path)


def test_config_template_round_trip_ok() -> None:
    """EDGE:config-template-round-trip: template parses via tomllib."""
    data = tomllib.loads(TEMPLATE)
    assert data["default_agent"] == "claude"
    assert len(data["agent"]) == 2


def test_load_config_reads_file(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('gui_editor = "nvim"\n')
    cfg = load_config(path)
    assert cfg.gui_editor == ["nvim"]


def test_build_layout_spec_resolves_agent() -> None:
    cfg = _parse({"agent": [{"pattern": "/r/*", "command": "claude-sandbox"}]})
    spec = build_layout_spec(cfg, Path("/r/repo"), agent_continue=True)
    assert spec.agent_cmd == ["claude-sandbox", "--continue"]
    assert isinstance(spec, LayoutSpec)


def test_layout_spec_defaults() -> None:
    spec = LayoutSpec.defaults()
    assert spec.terminal == TerminalSpec(
        bin="alacritty", cwd_flag="--working-directory", exec_flag="-e"
    )
    assert spec.agent_cmd == ["claude"]


def test_agent_rule_dataclass() -> None:
    r = AgentRule(pattern="/r/*", command=["x"])
    assert r.pattern == "/r/*"
