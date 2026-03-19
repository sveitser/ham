import argparse
import logging
import sys
from pathlib import Path

from ham import git, hyprland
from ham.executor import execute
from ham.git import DATA_DIR, worktree_path
from ham.orchestrator import plan_close, plan_delete, plan_open

log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog="ham", description="Hyprland Agent Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    open_parser = subparsers.add_parser("open")
    open_parser.add_argument("repo_path", type=Path)
    open_parser.add_argument("branch_name")

    for name in ("close", "delete"):
        sub = subparsers.add_parser(name)
        sub.add_argument("repo_path", type=Path, nargs="?")
        sub.add_argument("branch_name", nargs="?")

    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    logfile = DATA_DIR / "ham.log"
    logfile.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(logfile)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(fh)

    if args.command in ("close", "delete"):
        if args.repo_path and args.branch_name:
            repo = args.repo_path.resolve()
            branch = args.branch_name
            log.debug("explicit args: repo=%s branch=%s", repo, branch)
        else:
            resolved = git.resolve_from_cwd()
            if resolved is None:
                print("not in a ham worktree and no args given", file=sys.stderr)
                raise SystemExit(1)
            repo, branch = resolved
            log.debug("resolved from cwd: repo=%s branch=%s", repo, branch)
        wt_path = worktree_path(repo, branch)
    else:
        repo = args.repo_path.resolve()
        branch = args.branch_name
        wt_path = worktree_path(repo, branch)

    log.debug("worktree_path=%s", wt_path)

    match args.command:
        case "open":
            actions = plan_open(
                repo,
                branch,
                is_git_repo=git.is_git_repo(repo),
                worktree_exists=git.worktree_exists(repo, wt_path),
                branch_exists=git.branch_exists(repo, branch),
            )
        case "close":
            windows = hyprland.get_windows()
            actions = plan_close(repo, branch, windows)
        case "delete":
            dirty, status = git.is_dirty(wt_path)
            windows = hyprland.get_windows()
            actions = plan_delete(
                repo,
                branch,
                worktree_exists=git.worktree_exists(repo, wt_path),
                dirty=dirty,
                status=status,
                windows=windows,
            )

    execute(actions)


if __name__ == "__main__":
    main()
