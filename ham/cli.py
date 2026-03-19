import argparse
from pathlib import Path

from ham import git, hyprland
from ham.executor import execute
from ham.orchestrator import plan_close, plan_delete, plan_open


def main() -> None:
    parser = argparse.ArgumentParser(prog="ham", description="Hyprland Agent Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("open", "close", "delete"):
        sub = subparsers.add_parser(name)
        sub.add_argument("repo_path", type=Path)
        sub.add_argument("branch_name")

    args = parser.parse_args()
    repo = args.repo_path.resolve()
    branch = args.branch_name
    sanitized = git.sanitize_branch(branch)
    worktree_path = repo / ".wt" / sanitized

    match args.command:
        case "open":
            actions = plan_open(
                repo,
                branch,
                is_git_repo=git.is_git_repo(repo),
                worktree_exists=git.worktree_exists(repo, worktree_path),
                branch_exists=git.branch_exists(repo, branch),
            )
        case "close":
            windows = hyprland.get_windows()
            actions = plan_close(repo, branch, windows)
        case "delete":
            dirty, status = git.is_dirty(worktree_path)
            actions = plan_delete(
                repo,
                branch,
                worktree_exists=git.worktree_exists(repo, worktree_path),
                dirty=dirty,
                status=status,
            )

    execute(actions)


if __name__ == "__main__":
    main()
