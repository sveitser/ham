import logging
import os
import shlex
import shutil
import subprocess

from ham.actions import (
    Action,
    CloseWindow,
    GitWorktreeAdd,
    GitWorktreeRemove,
    LaunchProcess,
    PromptConfirmation,
    SetupDirenv,
    SwitchWorkspace,
)


log = logging.getLogger(__name__)


def execute(actions: list[Action], backend: str = "hyprland") -> None:
    log.info("%d actions to execute", len(actions))
    for action in actions:
        log.debug("executing %s", action)
        _execute_one(action, backend)


def _execute_one(action: Action, backend: str = "hyprland") -> None:
    match action:
        case GitWorktreeAdd(repo, worktree_path, branch, create_branch, start_point):
            cmd = ["git", "-C", str(repo), "worktree", "add"]
            if create_branch:
                cmd.extend(["-b", branch])
            cmd.append(str(worktree_path))
            if create_branch and start_point is not None:
                cmd.append(start_point)
            elif not create_branch:
                cmd.append(branch)
            subprocess.run(cmd, check=True)

        case GitWorktreeRemove(repo, worktree_path, force):
            cmd = ["git", "-C", str(repo), "worktree", "remove"]
            if force:
                cmd.append("--force")
            cmd.append(str(worktree_path))
            subprocess.run(cmd, check=True)

        case SetupDirenv(cwd):
            envrc_example = cwd / ".envrc.example"
            envrc_local = cwd / ".envrc.local"
            if envrc_example.exists() and not envrc_local.exists():
                log.info("copying .envrc.example to .envrc.local")
                shutil.copy2(envrc_example, envrc_local)
            envrc = cwd / ".envrc"
            if not envrc.exists():
                log.debug("no .envrc found, skipping direnv allow")
                return
            result = subprocess.run(
                ["direnv", "allow"],
                cwd=str(cwd),
            )
            if result.returncode != 0:
                log.warning(
                    "direnv allow failed (rc=%d), continuing", result.returncode
                )

        case LaunchProcess(cmd, workspace_id, cwd):
            if backend == "tmux":
                has = (
                    subprocess.run(
                        ["tmux", "has-session", "-t", workspace_id],
                        capture_output=True,
                    ).returncode
                    == 0
                )
                if has:
                    tmux_cmd = [
                        "tmux",
                        "new-window",
                        "-t",
                        workspace_id,
                        "-c",
                        str(cwd),
                        "--",
                    ] + cmd
                else:
                    tmux_cmd = [
                        "tmux",
                        "new-session",
                        "-d",
                        "-s",
                        workspace_id,
                        "-c",
                        str(cwd),
                        "--",
                    ] + cmd
                subprocess.run(tmux_cmd, check=True)
            else:
                shell_cmd = " ".join(shlex.quote(c) for c in cmd)
                subprocess.run(
                    [
                        "hyprctl",
                        "dispatch",
                        "exec",
                        f"[workspace {workspace_id} silent]",
                        shell_cmd,
                    ],
                    check=True,
                )

        case CloseWindow(window_id):
            if backend == "tmux":
                subprocess.run(["tmux", "kill-window", "-t", window_id], check=True)
            else:
                subprocess.run(
                    ["hyprctl", "dispatch", "closewindow", f"address:{window_id}"],
                    check=True,
                )

        case SwitchWorkspace(workspace_id):
            if backend == "tmux":
                if os.environ.get("TMUX"):
                    subprocess.run(
                        ["tmux", "switch-client", "-t", workspace_id], check=True
                    )
                else:
                    subprocess.run(
                        ["tmux", "attach-session", "-t", workspace_id], check=True
                    )
            else:
                subprocess.run(
                    ["hyprctl", "dispatch", "workspace", workspace_id],
                    check=True,
                )

        case PromptConfirmation(message):
            print(message)
            answer = input("Continue? [y/N] ")
            if answer.lower() != "y":
                raise SystemExit("aborted")

        case _:
            raise TypeError(f"unknown action: {action}")
