# ham - Hyprland Agent Manager

Workspace management for [Hyprland](https://hyprland.org/) + [Claude Code](https://claude.com/claude-code). Each repo/branch gets its own workspace with an editor and agent terminal.

## Requirements

Opinionated and only works with:

- [Hyprland](https://hyprland.org/) (window manager / workspaces)
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
