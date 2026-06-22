import argparse
import logging
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from ham import git, recency
from ham.backend import detect_backend
from ham.config import CONFIG_PATH, Config, init_config, load_config
from ham.executor import execute
from ham.git import DATA_DIR, WorktreeStatus, worktree_path
from ham.actions import Action, SwitchWorkspace
from ham._version import GIT_DATE, GIT_REV, VERSION
from ham.orchestrator import plan_close, plan_delete, plan_switch, plan_switch_repo

log = logging.getLogger(__name__)


def _version_str() -> str:
    rev, ts = GIT_REV, GIT_DATE
    if "@" in rev:
        pkg_dir = Path(__file__).parent
        try:
            rev = subprocess.run(
                ["git", "-C", str(pkg_dir), "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            epoch = subprocess.run(
                ["git", "-C", str(pkg_dir), "log", "-1", "--format=%ct"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            ts = datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime(
                "%Y-%m-%d_%H_%M_%S"
            )
        except Exception:
            rev, ts = "dev", "unknown"
    return f"{VERSION}+{rev}.{ts}"


def _resolve_selection(selection: str) -> tuple[Path, str | None]:
    """Parse a 'wt: name/branch' or 'repo: name' selection (prefix optional for worktrees)."""
    if selection.startswith("repo: "):
        name = selection[len("repo: ") :]
        try:
            return (git.resolve_repo(name), None)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            raise SystemExit(1)
    target = selection[len("wt: ") :] if selection.startswith("wt: ") else selection
    resolved = git.resolve_worktree(target)
    if resolved is None:
        print(f"worktree not found: {target}", file=sys.stderr)
        raise SystemExit(1)
    return (resolved[0], resolved[1])


def _entry_flag(s: WorktreeStatus) -> str:
    return ("M" if s.has_modified else "") + ("?" if s.has_untracked else "")


def _worktree_lines(worktrees: list[WorktreeStatus]) -> list[str]:
    """Format worktrees as picker lines, newest Claude session first, with an age column."""
    now = time.time()
    dated = [(recency.last_session_mtime(s.wt_path), s) for s in worktrees]
    dated.sort(key=lambda t: (t[0] is not None, t[0] or 0.0), reverse=True)
    return [
        f"wt: {s.repo_name}/{s.branch}\t{recency.format_age(m, now)}\t{_entry_flag(s)}"
        for m, s in dated
    ]


def _repo_lines(repos: list[Path]) -> list[str]:
    return [f"repo: {p.name}\t\t" for p in repos]


def picker_entries() -> list[str]:
    worktrees = git.list_worktree_status()
    repos = git.discover_repos()
    return _worktree_lines(worktrees) + _repo_lines(repos)


def _workspace_label(windows, worktrees) -> str:
    resolved_wts = [(wt.wt_path.resolve(), wt) for wt in worktrees]
    for w in windows:
        for cwd in w.cwds:
            cwd_r = cwd.resolve()
            for wt_path, wt in resolved_wts:
                if cwd_r.is_relative_to(wt_path):
                    return f"{wt.repo_name}/{wt.branch}"
    seen: set[str] = set()
    classes = [
        c for w in windows if (c := w.class_name) not in seen and not seen.add(c)
    ]  # type: ignore[func-returns-value]
    return " ".join(classes)


def _workspace_entries(backend, worktrees) -> list[str]:
    windows = backend.get_windows()
    if backend.name == "hyprland":
        ws: dict[int, list] = {}
        for w in windows:
            ws.setdefault(w.workspace_id, []).append(w)
        return [
            f"ws: {ws_id}\t{_workspace_label(ws_windows, worktrees)}"
            for ws_id, ws_windows in sorted(ws.items())
        ]
    else:
        sessions = sorted({w.session_name for w in windows})
        return [f"ws: {s}\t" for s in sessions]


def _get_selection(args: argparse.Namespace, backend) -> tuple[Path, str | None]:
    """Pick a worktree or repo. Returns (repo_path, branch) or (repo_path, None)."""
    if args.command != "rofi" and getattr(args, "query", None):
        return _resolve_selection(args.query)

    worktrees = git.list_worktree_status()
    repos = git.discover_repos()
    entries = (
        _workspace_entries(backend, worktrees)
        + _worktree_lines(worktrees)
        + _repo_lines(repos)
    )
    if not entries:
        print("no worktrees or repos found", file=sys.stderr)
        raise SystemExit(1)

    if args.command == "rofi":
        cmd = ["rofi", "-dmenu", "-p", "ham", "-i"]
    else:
        ham_cmd = shlex.join([sys.executable, "-m", "ham.cli"])
        bind = f"ctrl-d:execute({ham_cmd} delete {{1}})+reload({ham_cmd} _entries)"
        cmd = [
            "fzf",
            "--prompt",
            "ham> ",
            "--header",
            "enter: switch   ctrl-d: delete   esc: quit",
            "--delimiter",
            "\t",
            "--bind",
            bind,
        ]
    result = subprocess.run(
        cmd, input="\n".join(entries), capture_output=True, text=True
    )
    if result.returncode != 0:
        raise SystemExit(1)
    selection = result.stdout.strip().split("\t", 1)[0]
    if selection.startswith("ws: "):
        ws_id = selection[len("ws: ") :]
        execute([SwitchWorkspace(workspace_id=ws_id)], backend.name)
        raise SystemExit(0)
    return _resolve_selection(selection)


def _pick_repo() -> Path:
    """fzf picker over discovered repos."""
    repos = git.discover_repos()
    if not repos:
        print(f"no repos found in {git.REPO_DIR}", file=sys.stderr)
        raise SystemExit(1)
    result = subprocess.run(
        ["fzf", "--prompt", "repo> "],
        input="\n".join(str(r) for r in repos),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(1)
    return Path(result.stdout.strip())


def _pick_branch(repo: Path) -> str:
    """fzf picker over branches, with --print-query for new branch names."""
    branches = git.list_branches(repo)
    result = subprocess.run(
        ["fzf", "--print-query", "--prompt", "branch> "],
        input="\n".join(branches) if branches else "",
        capture_output=True,
        text=True,
    )
    # --print-query: line 0 = typed query, line 1 = selected match
    # rc=0: match selected, rc=1: no match (use query as new branch name)
    lines = result.stdout.strip().splitlines()
    if result.returncode == 0 and len(lines) >= 2:
        return lines[1]
    if result.returncode == 1 and len(lines) >= 1 and lines[0]:
        return lines[0]
    raise SystemExit(1)


def _target_workspace(backend, hint: str = "") -> str:
    """Reuse current workspace if it has <= 1 window, else pick a free one."""
    if backend.name == "tmux":
        return backend.find_free_workspace(hint)
    active_id, count = backend.get_active_workspace()
    return active_id if count <= 1 else backend.find_free_workspace()


def _switch_actions(
    repo: Path,
    branch: str,
    backend,
    config: Config,
    *,
    start_point: str | None = None,
) -> list[Action]:
    """Build plan_switch actions for a repo/branch."""
    wt_path = worktree_path(repo, branch)
    windows = backend.get_windows()
    matched = backend.windows_in_path(windows, wt_path, own_last=False)
    workspace_id = backend.get_workspace_for_windows(matched)
    is_repo = git.is_git_repo(repo)
    wt_exists = git.worktree_exists(repo, wt_path)
    if is_repo and not wt_exists:
        git.fetch_origin(repo)
    hint = f"{repo.name}-{git.sanitize_branch(branch)}"
    return plan_switch(
        repo,
        branch,
        workspace_id=workspace_id,
        free_workspace=_target_workspace(backend, hint)
        if workspace_id is None
        else "0",
        is_git_repo=is_repo,
        worktree_exists=wt_exists,
        branch_exists=git.branch_exists(repo, branch),
        remote_branch_exists=git.remote_branch_exists(repo, branch),
        backend=backend,
        start_point=start_point,
        config=config,
    )


def _switch_repo_actions(repo: Path, backend, config: Config) -> list[Action]:
    """Build plan_switch_repo actions for a bare repo path (no worktree)."""
    windows = backend.get_windows()
    matched = backend.windows_in_path(windows, repo, own_last=False)
    workspace_id = backend.get_workspace_for_windows(matched)
    hint = repo.name
    return plan_switch_repo(
        repo,
        workspace_id=workspace_id,
        free_workspace=_target_workspace(backend, hint)
        if workspace_id is None
        else "0",
        backend=backend,
        config=config,
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="ham", description="Hyprland Agent Manager")
    subparsers = parser.add_subparsers(dest="command")

    open_parser = subparsers.add_parser(
        "open", help="open or switch to worktree (interactive fzf if no args)"
    )
    open_parser.add_argument(
        "target", nargs="?", help="repo_name/branch or repo_path (with branch_name)"
    )
    open_parser.add_argument("branch_name", nargs="?", help="branch name")
    open_parser.add_argument(
        "--from",
        dest="start_point",
        default=None,
        help="start point for new branches (default: origin/main)",
    )

    for name, help_text in (
        ("close", "close workspace windows for a worktree"),
        ("delete", "delete worktree, branch, and close windows"),
    ):
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument(
            "target", nargs="?", help="repo_name/branch or repo_path (with branch_name)"
        )
        sub.add_argument("branch_name", nargs="?", help="branch name")

    subparsers.add_parser("list", help="list active worktrees as repo_name/branch")

    switch_parser = subparsers.add_parser(
        "switch",
        help="focus existing workspace, or open worktree if no windows (fzf picker if no query)",
    )
    switch_parser.add_argument("query", nargs="?", help="repo_name/branch to switch to")

    subparsers.add_parser("rofi", help="switch to worktree via rofi picker")

    subparsers.add_parser("_entries")
    subparsers.add_parser("version", help="show version and git info")
    subparsers.add_parser("init", help="write a starter config file")

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

    if args.command == "init":
        try:
            p = init_config()
        except FileExistsError:
            print(f"config already exists: {CONFIG_PATH}", file=sys.stderr)
            raise SystemExit(1)
        print(f"wrote {p}")
        return

    config = load_config()
    if config.repo_dir is not None:
        git.REPO_DIR = config.repo_dir

    backend = detect_backend()

    if args.command == "version":
        print(_version_str())
        return

    if args.command == "list":
        for repo_name, branch in git.list_worktrees():
            print(f"{repo_name}/{branch}")
        return

    if args.command == "_entries":
        for line in picker_entries():
            print(line)
        return

    if args.command in (None, "switch", "rofi"):
        repo, branch = _get_selection(args, backend)
        if branch is None:
            execute(_switch_repo_actions(repo, backend, config), backend.name)
        else:
            execute(_switch_actions(repo, branch, backend, config), backend.name)
        return

    if args.command in ("close", "delete"):
        if args.target and args.target.startswith("repo: "):
            if args.command == "delete":
                print("cannot delete a repo entry", file=sys.stderr)
                raise SystemExit(1)
            name = args.target[len("repo: ") :]
            try:
                repo = git.resolve_repo(name)
            except ValueError as e:
                print(str(e), file=sys.stderr)
                raise SystemExit(1)
            branch = None
        else:
            if args.target:
                args.target = args.target.removeprefix("wt: ")
            if args.target and args.branch_name:
                repo = Path(args.target).resolve()
                branch = args.branch_name
                log.debug("explicit args: repo=%s branch=%s", repo, branch)
            elif args.target:
                resolved = git.resolve_worktree(args.target)
                if resolved is None:
                    print(f"worktree not found: {args.target}", file=sys.stderr)
                    raise SystemExit(1)
                repo, branch = resolved
                log.debug("resolved from target: repo=%s branch=%s", repo, branch)
            else:
                resolved = git.resolve_from_cwd()
                if resolved is not None:
                    repo, branch = resolved
                    log.debug("resolved from cwd: repo=%s branch=%s", repo, branch)
                elif args.command == "close":
                    root = git.git_root_from_cwd()
                    if root is None:
                        print("not in a git repo and no args given", file=sys.stderr)
                        raise SystemExit(1)
                    repo, branch = root, None
                    log.debug("resolved repo from cwd: repo=%s", repo)
                else:
                    print("not in a ham worktree and no args given", file=sys.stderr)
                    raise SystemExit(1)
        wt_path = worktree_path(repo, branch) if branch is not None else repo
    else:
        # Resolve target to (repo, branch)
        if args.target is None:
            # Interactive: fzf repo then branch
            repo = _pick_repo()
            branch = _pick_branch(repo)
        elif args.branch_name is not None:
            # Explicit: ham open /path branch
            repo = Path(args.target).resolve()
            branch = args.branch_name
        else:
            # Smart resolution: ham open foo/bar/baz
            resolved = git.resolve_worktree(args.target)
            if resolved is not None:
                repo, branch = resolved
            else:
                parts = args.target.split("/", 1)
                if len(parts) != 2:
                    print(
                        f"invalid target (need repo/branch): {args.target}",
                        file=sys.stderr,
                    )
                    raise SystemExit(1)
                repo_name, branch = parts
                try:
                    repo = git.resolve_repo(repo_name)
                except ValueError as e:
                    print(str(e), file=sys.stderr)
                    raise SystemExit(1)
        wt_path = worktree_path(repo, branch)

    log.debug("worktree_path=%s", wt_path)

    match args.command:
        case "open":
            start_point = (
                args.start_point
                if args.start_point is not None
                else config.default_start_point
            )
            actions = _switch_actions(
                repo, branch, backend, config, start_point=start_point
            )
        case "close":
            windows = backend.get_windows()
            matched = backend.windows_in_path(windows, wt_path)
            actions = plan_close(matched)
        case "delete":
            dirty, status = git.is_dirty(wt_path)
            windows = backend.get_windows()
            matched = backend.windows_in_path(windows, wt_path)
            actions = plan_delete(
                repo,
                branch,
                worktree_exists=git.worktree_exists(repo, wt_path),
                dirty=dirty,
                status=status,
                windows=matched,
            )
        case _:  # pragma: no cover
            raise AssertionError(f"unhandled command: {args.command}")

    execute(actions, backend.name)


if __name__ == "__main__":  # pragma: no cover
    main()
