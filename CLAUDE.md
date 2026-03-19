# ham - Hyprland Agent Manager

Workspace management tool for hyprland + Claude Code.

## Commands
- `nix develop` - enter dev shell
- `pytest` - run tests
- `python -m ham.cli` - run without installing

## Architecture
- Action/Effect pattern: orchestrator produces `list[Action]`, executor runs them
- Tests assert on action lists, no mocking needed
- `ham/orchestrator.py` - business logic
- `ham/actions.py` - action dataclasses
- `ham/executor.py` - runs actions
- `ham/hyprland.py` - hyprctl queries
- `ham/git.py` - git worktree ops
