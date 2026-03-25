# ham - Hyprland Agent Manager

Workspace management tool for hyprland + Claude Code.

## Commands
- `nix develop` - enter dev shell
- `python -m ham.cli` - run without installing
- `just test` - run tests
- `just cov` - tests with coverage
- `just fmt` - format with ruff
- `just lint` - lint with ruff
- `just check` - fmt + lint + cov

## CLI Usage
- `ham open` - interactive fzf: pick repo from REPO_DIR, then pick/type branch
- `ham open repo_name/branch` - resolve existing worktree or discover repo in REPO_DIR
- `ham open /path/to/repo branch` - explicit repo path + branch
- `ham list` - list active worktrees as repo_name/branch
- `ham switch [query]` - focus existing worktree workspace (fzf if no query)
- `ham rofi` - switch via rofi picker
- `ham close [repo_name/branch | repo_path branch]` - close workspace windows (resolves from cwd if no args)
- `ham delete [repo_name/branch | repo_path branch]` - delete worktree and close windows

## Environment
- `HAM_REPO_DIR` - repo discovery root (default: `~/r`), scanned 2 levels deep (org/repo)

## Architecture
- Action/Effect pattern: orchestrator produces `list[Action]`, executor runs them
- Tests assert on action lists, no mocking needed
- `ham/orchestrator.py` - business logic (plan_open, plan_close, plan_delete, plan_switch)
- `ham/actions.py` - action dataclasses
- `ham/executor.py` - runs actions
- `ham/hyprland.py` - hyprctl queries
- `ham/git.py` - git worktree ops + repo discovery
