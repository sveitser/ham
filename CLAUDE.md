# ham - Hyprland Agent Manager

Workspace management tool for hyprland + Claude Code. Also works headless via tmux.

## Commands
- `nix develop` - enter dev shell
- `python -m ham.cli` - run without installing
- `just test` - run tests
- `just cov` - tests with coverage
- `just fmt` - format with ruff
- `just lint` - lint with ruff
- `just check` - fmt + lint + cov

## CLI Usage
- `ham` - default fzf picker over worktrees + repos (`wt: ...` / `repo: ...` entries with `M`/`?` flags); `enter` switches, `ctrl-d` deletes the worktree
- `ham open` - interactive fzf: pick repo from REPO_DIR, then pick/type branch
- `ham open repo_name/branch` - resolve existing worktree or discover repo in REPO_DIR
- `ham open /path/to/repo branch` - explicit repo path + branch
- `ham open ... --from REF` - start new branches from REF instead of `origin/main`
- When spawning new windows, reuses the active workspace if it has ≤1 window, else picks the lowest free one (Hyprland only)
- `ham list` - list active worktrees as repo_name/branch
- `ham switch [query]` - same as `ham`; with query it directly resolves and switches
- `ham rofi` - same picker via rofi (no ctrl-d binding)
- `ham close [repo_name/branch | repo_path branch]` - close workspace windows (resolves from cwd if no args)
- `ham delete [repo_name/branch | repo_path branch]` - delete worktree and close windows (also accepts `wt: repo/branch` from picker)
- `ham init` - write a starter config file (errors if one already exists)

## Environment
- `HAM_REPO_DIR` - repo discovery root (default: `~/r`), scanned 2 levels deep (org/repo)

## Config file
Optional TOML at `platformdirs.user_config_path("ham")/config.toml` (Linux `~/.config/ham/config.toml`, macOS `~/Library/Application Support/ham/config.toml`). Absent file = built-in defaults. `ham init` writes a starter. Command values are TOML strings, `shlex.split` at load.

Keys (all optional):
- `terminal` - terminal emulator (Hyprland only). Default: infer from `$TERM_PROGRAM` (macOS) / `$TERM` (Linux), else alacritty
- `gui_editor` - editor that opens `<worktree>/<readme_file>`. Default `emacs`
- `headless_editor` - tmux editor for the worktree dir. Default `emacs -nw`
- `readme_file` - file opened by gui_editor. Default `README.md`
- `use_direnv` - wrap launched commands in `direnv exec <cwd>`. Default `true`
- `default_agent` - agent command when no `[[agent]]` rule matches. Default `claude`
- `agent_continue_default` - force `--continue` when opening. Default `false`
- `repo_dir` - overrides `$HAM_REPO_DIR`
- `default_start_point` - default `--from` ref for new branches. Default `origin/main`
- `[[agent]]` rules - `pattern` (glob on source repo path, `~` expanded) + `command`. Deepest/most-specific match wins, order-independent

## Backend
Backend is auto-detected:
- **Hyprland**: `$HYPRLAND_INSTANCE_SIGNATURE` set → uses `hyprctl`, opens Alacritty + Emacs + Claude windows in a numeric workspace
- **tmux**: fallback → creates a named session (`repo-branch`) with 3 panes: emacs -nw (left), claude (top-right), shell (bottom-right)

## Architecture
- Action/Effect pattern: orchestrator produces `list[Action]`, executor runs them
- Tests assert on action lists, no mocking needed
- `ham/orchestrator.py` - backend-agnostic business logic; receives pre-filtered windows, never imports from `ham.hyprland` or `ham.tmux`
- `ham/actions.py` - action dataclasses
- `ham/executor.py` - runs actions
- `ham/backend.py` - `Backend` protocol + `HyprlandBackend`/`TmuxBackend`; owns `windows_in_path`, `get_windows`, `layout_actions`
- `ham/hyprland.py` - hyprctl queries (Hyprland-specific)
- `ham/tmux.py` - tmux queries (tmux-specific)
- `ham/git.py` - git worktree ops + repo discovery
- `ham/config.py` - TOML config: `Config`/`LayoutSpec`, `load_config`, `init_config`, `resolve_terminal`, `build_layout_spec`; orchestrator builds a `LayoutSpec` (repo-resolved agent/editor/terminal) and passes it to the backend
- `ham/cli.py` - argument parsing; loads config, calls `backend.windows_in_path` to filter windows before passing to orchestrator

**Layer rule**: window filtering always happens in `cli.py` via `backend.windows_in_path`; orchestrator functions (`plan_close`, `plan_delete`) receive already-matched windows.
