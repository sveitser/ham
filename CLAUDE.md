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
- When spawning new windows, reuses the active workspace if it has ≤1 window, else picks the lowest free one (Hyprland only)
- `ham list` - list active worktrees as repo_name/branch
- `ham switch [query]` - same as `ham`; with query it directly resolves and switches
- `ham rofi` - same picker via rofi (no ctrl-d binding)
- `ham close [repo_name/branch | repo_path branch]` - close workspace windows (resolves from cwd if no args)
- `ham delete [repo_name/branch | repo_path branch]` - delete worktree and close windows (also accepts `wt: repo/branch` from picker)

## Environment
- `HAM_REPO_DIR` - repo discovery root (default: `~/r`), scanned 2 levels deep (org/repo)

## Backend
Backend is auto-detected:
- **Hyprland**: `$HYPRLAND_INSTANCE_SIGNATURE` set → uses `hyprctl`, opens Alacritty + Emacs + Claude windows in a numeric workspace
- **tmux**: fallback → creates a named session (`repo-branch`) with 3 panes: emacs -nw (left), claude (top-right), shell (bottom-right)

## Architecture
- Action/Effect pattern: orchestrator produces `list[Action]`, executor runs them
- Tests assert on action lists, no mocking needed
- `ham/orchestrator.py` - business logic (plan_open, plan_close, plan_delete, plan_switch)
- `ham/actions.py` - action dataclasses
- `ham/executor.py` - runs actions
- `ham/backend.py` - backend protocol + Hyprland/tmux implementations (layout_actions, get_windows, etc.)
- `ham/hyprland.py` - hyprctl queries
- `ham/tmux.py` - tmux queries
- `ham/git.py` - git worktree ops + repo discovery
