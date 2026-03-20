import logging
import os
import shutil
import subprocess

from ham.actions import (
    Action,
    CloseWindow,
    ExecProcess,
    GitWorktreeAdd,
    GitWorktreeRemove,
    LaunchProcess,
    PromptConfirmation,
    SetupDirenv,
    SwitchWorkspace,
)


log = logging.getLogger(__name__)


def execute(actions: list[Action]) -> None:
    log.info("%d actions to execute", len(actions))
    for action in actions:
        log.debug("executing %s", action)
        _execute_one(action)


def _execute_one(action: Action) -> None:
    match action:
        case GitWorktreeAdd(repo, worktree_path, branch, create_branch):
            cmd = ["git", "-C", str(repo), "worktree", "add"]
            if create_branch:
                cmd.extend(["-b", branch])
            cmd.append(str(worktree_path))
            if not create_branch:
                cmd.append(branch)
            subprocess.run(cmd, check=True)

        case GitWorktreeRemove(repo, worktree_path):
            subprocess.run(
                ["git", "-C", str(repo), "worktree", "remove", str(worktree_path)],
                check=True,
            )

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

        case LaunchProcess(cmd, cwd):
            subprocess.Popen(
                cmd,
                cwd=str(cwd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

        case CloseWindow(address):
            subprocess.run(
                ["hyprctl", "dispatch", "closewindow", f"address:{address}"],
                check=True,
            )

        case ExecProcess(cmd, cwd, fallback_cmd):
            os.chdir(cwd)
            if fallback_cmd:
                result = subprocess.run(cmd)
                if result.returncode != 0:
                    os.execvp(fallback_cmd[0], fallback_cmd)
            else:
                os.execvp(cmd[0], cmd)

        case SwitchWorkspace(workspace_id):
            subprocess.run(
                ["hyprctl", "dispatch", "workspace", str(workspace_id)],
                check=True,
            )

        case PromptConfirmation(message):
            print(message)
            answer = input("Continue? [y/N] ")
            if answer.lower() != "y":
                raise SystemExit("aborted")

        case _:
            raise TypeError(f"unknown action: {action}")
