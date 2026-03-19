import subprocess

from ham.actions import (
    Action,
    CloseWindow,
    GitWorktreeAdd,
    GitWorktreeRemove,
    LaunchProcess,
    PromptConfirmation,
)


def execute(actions: list[Action]) -> None:
    for action in actions:
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

        case PromptConfirmation(message):
            print(message)
            answer = input("Continue? [y/N] ")
            if answer.lower() != "y":
                raise SystemExit("aborted")

        case _:
            raise TypeError(f"unknown action: {action}")
