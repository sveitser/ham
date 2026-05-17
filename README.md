# ham - Hyprland Agent Manager

Workspace management for running multiple [Claude Code](https://claude.com/claude-code) agents in
parallel. One agent per branch, each in its own workspace. Works with
[Hyprland](https://hyprland.org/) or headless via [tmux](https://github.com/tmux/tmux).

## What it does

`ham open repo/branch` sets up a branch for an agent to work on:

1. Creates a git worktree (new branch if it doesn't exist)
2. Opens a workspace and launches three windows/panes:
   - **Emacs** (editor)
   - **Claude Code** (agent; `--continue` if resuming)
   - **Shell** in the worktree
3. Wraps editor and agent with `direnv exec` so project env vars load automatically

The backend is auto-detected via `$HYPRLAND_INSTANCE_SIGNATURE`:
- **Hyprland**: opens Alacritty + Emacs + Claude in a numeric workspace
- **tmux**: creates a named session (`repo-branch`) with 3 panes — `emacs -nw` left, Claude top-right, shell bottom-right

Lifecycle:

- `ham open` - create worktree + workspace
- `ham switch` / `ham rofi` - jump back to a running workspace
- `ham list` - see active worktrees
- `ham close` - close the workspace windows (worktree stays)
- `ham delete` - close windows and remove the worktree (confirms if dirty)

## Requirements

- [Git](https://git-scm.com/) (worktrees)
- [Claude Code](https://claude.com/claude-code) (agent)
- [Emacs](https://www.gnu.org/software/emacs/) (editor)
- **Hyprland mode**: [Hyprland](https://hyprland.org/), [Alacritty](https://alacritty.org/)
- **tmux mode**: [tmux](https://github.com/tmux/tmux)

## Install

```sh
nix profile install github:sveitser/ham   # install from flake
nix run github:sveitser/ham -- open       # run without installing
```

## Usage

```sh
ham open                          # fzf: pick repo, then branch
ham open repo/branch              # resolve from $HAM_REPO_DIR
ham open /path/to/repo branch     # explicit path
ham list                          # active worktrees
ham switch [query]                # focus workspace (fzf if no query)
ham rofi                          # switch via rofi
ham close [repo/branch]           # close workspace windows
ham delete [repo/branch]          # delete worktree + close windows
```

## Environment

- `HAM_REPO_DIR` - repo discovery root (default `~/r`), scanned 2 levels deep (`org/repo`).

## Development

Activate the dev shell with [direnv](https://direnv.net/) (`direnv allow`) or manually:

```sh
nix develop    # enter dev shell
nix build      # build package
just test      # pytest
just cov       # with coverage
just check     # fmt + lint + cov
```

## License

MIT - see [LICENSE](LICENSE).
