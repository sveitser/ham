import argparse
import logging
import subprocess
import sys
from pathlib import Path

from ham import git, hyprland
from ham.executor import execute
from ham.git import DATA_DIR, worktree_path
from ham.hyprland import find_free_workspace, get_workspace_for_windows, windows_in_path
from ham.orchestrator import plan_close, plan_delete, plan_open, plan_switch

log = logging.getLogger(__name__)


def _get_selection(args: argparse.Namespace) -> str:
    """Get worktree selection from args, fzf, or rofi."""
    entries = [f"{name}/{branch}" for name, branch in git.list_worktrees()]
    if not entries:
        print("no worktrees found", file=sys.stderr)
        raise SystemExit(1)

    if args.command == "rofi":
        result = subprocess.run(
            ["rofi", "-dmenu", "-p", "ham", "-i"],
            input="\n".join(entries),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise SystemExit(1)
        return result.stdout.strip()

    if args.query:
        for entry in entries:
            if entry == args.query:
                return entry
        print(f"no match for: {args.query}", file=sys.stderr)
        raise SystemExit(1)

    result = subprocess.run(
        ["fzf"],
        input="\n".join(entries),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(1)
    return result.stdout.strip()


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

    subparsers.add_parser("list")

    switch_parser = subparsers.add_parser("switch")
    switch_parser.add_argument("query", nargs="?")

    subparsers.add_parser("rofi")

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

    if args.command == "list":
        for repo_name, branch in git.list_worktrees():
            print(f"{repo_name}/{branch}")
        return

    if args.command in ("switch", "rofi"):
        selection = _get_selection(args)
        resolved = git.resolve_worktree(selection)
        if resolved is None:
            print(f"worktree not found: {selection}", file=sys.stderr)
            raise SystemExit(1)
        repo, branch = resolved
        wt_path = worktree_path(repo, branch)
        windows = hyprland.get_windows()
        matched = windows_in_path(windows, wt_path, own_last=False)
        workspace_id = get_workspace_for_windows(matched)
        actions = plan_switch(
            repo,
            branch,
            workspace_id=workspace_id,
            free_workspace=find_free_workspace() if workspace_id is None else 0,
            is_git_repo=git.is_git_repo(repo),
            worktree_exists=git.worktree_exists(repo, wt_path),
            branch_exists=git.branch_exists(repo, branch),
        )
        execute(actions)
        return

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
