import logging
import os
import shlex
import shutil
import subprocess

from ham.actions import (
    Action,
    CloseWindow,
    GitSetBranchUpstream,
    GitWorktreeAdd,
    GitWorktreeRemove,
    LaunchProcess,
    PromptConfirmation,
    SetupDirenv,
    SwitchWorkspace,
    TmuxLayout,
)


log = logging.getLogger(__name__)


def execute(actions: list[Action], backend: str = "hyprland") -> None:
    log.info("%d actions to execute", len(actions))
    for action in actions:
        log.debug("executing %s", action)
        _execute_one(action, backend)


def _execute_one(action: Action, backend: str = "hyprland") -> None:
    match action:
        case GitWorktreeAdd(
            repo, worktree_path, branch, create_branch, start_point, no_track
        ):
            cmd = ["git", "-C", str(repo), "worktree", "add"]
            if no_track:
                cmd.append("--no-track")
            if create_branch:
                cmd.extend(["-b", branch])
            cmd.append(str(worktree_path))
            if create_branch and start_point is not None:
                cmd.append(start_point)
            elif not create_branch:
                cmd.append(branch)
            subprocess.run(cmd, check=True)

        case GitSetBranchUpstream(repo, branch):
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "config",
                    f"branch.{branch}.remote",
                    "origin",
                ],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "config",
                    f"branch.{branch}.merge",
                    f"refs/heads/{branch}",
                ],
                check=True,
            )

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

        case LaunchProcess(cmd, workspace_id, _):
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

        case TmuxLayout(session_name, cwd, emacs_cmd, agent_cmd):
            has = (
                subprocess.run(
                    ["tmux", "has-session", "-t", session_name], capture_output=True
                ).returncode
                == 0
            )
            if not has:
                subprocess.run(
                    ["tmux", "new-session", "-d", "-s", session_name, "-c", str(cwd)],
                    check=True,
                )
            else:
                subprocess.run(
                    ["tmux", "new-window", "-d", "-t", session_name, "-c", str(cwd)],
                    check=True,
                )
            subprocess.run(
                [
                    "tmux",
                    "split-window",
                    "-h",
                    "-t",
                    f"{session_name}:0.0",
                    "-c",
                    str(cwd),
                ],
                check=True,
            )
            subprocess.run(
                [
                    "tmux",
                    "split-window",
                    "-v",
                    "-t",
                    f"{session_name}:0.1",
                    "-c",
                    str(cwd),
                ],
                check=True,
            )
            subprocess.run(
                [
                    "tmux",
                    "send-keys",
                    "-t",
                    f"{session_name}:0.0",
                    shlex.join(emacs_cmd),
                    "Enter",
                ],
                check=True,
            )
            subprocess.run(
                [
                    "tmux",
                    "send-keys",
                    "-t",
                    f"{session_name}:0.1",
                    shlex.join(agent_cmd),
                    "Enter",
                ],
                check=True,
            )
            subprocess.run(
                ["tmux", "select-pane", "-t", f"{session_name}:0.2"], check=True
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
