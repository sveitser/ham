# ham - Hyprland Agent Manager

Workspace management for running multiple [Claude Code](https://claude.com/claude-code) agents in
parallel on [Hyprland](https://hyprland.org/). One agent per branch, each in its own workspace.

## What it does

`ham open repo/branch` sets up a branch for an agent to work on:

1. Creates a git worktree at `repo-branch/` (new branch if it doesn't exist)
2. Opens a fresh Hyprland workspace and launches three windows pinned to it:
   - **Alacritty** in the worktree (shell)
   - **Emacs** opening `README.md` (editor)
   - **Alacritty** running `claude` (agent; `--continue` if resuming)
3. Wraps editor and agent with `direnv exec` so project env vars load automatically

Lifecycle:

- `ham open` - create worktree + workspace
- `ham switch` / `ham rofi` - jump back to a running workspace
- `ham list` - see active worktrees
- `ham close` - close the workspace windows (worktree stays)
- `ham delete` - close windows and remove the worktree (confirms if dirty)

## Requirements

Opinionated and only works with:

- [Hyprland](https://hyprland.org/) (window manager / workspaces)
- [Alacritty](https://alacritty.org/) (terminal)
- [Emacs](https://www.gnu.org/software/emacs/) (editor)
- [Git](https://git-scm.com/) (worktrees)
- [Claude Code](https://claude.com/claude-code) (agent)

## Install

```sh
nix profile install github:sveitser/agent-manager   # install from flake
nix run github:sveitser/agent-manager -- open       # run without installing
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
