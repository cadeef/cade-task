import json
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError, run


def list_resolve(project_dir: str, working_dir: str | None = None) -> str | None:
    if working_dir:
        cwd = Path(working_dir)
    else:
        cwd = Path.cwd()

    # Is project dir part of cwd?
    try:
        project_dir_relative = cwd.relative_to(project_dir)
    except ValueError:
        return None

    # Project_dir and workding dir are the same? (project_path)
    if project_dir_relative == Path("."):
        return None

    try:
        # In a nested directory of a project? (project_path/<project>/yup)
        project = project_dir_relative.parents[1]
    except IndexError:
        # Must be in base project directory (project_path/<project>)
        project = project_dir_relative

    return str(project)


def get_tasks(project: str) -> list[str]:
    try:
        tasks = run_and_return(["show", project], mode="json")
    except TaskCommandException as e:
        if "No reminders list matching" in e.output:
            raise ListNotFoundException(f"List '{project}' not found")
        else:
            raise

    return tasks


def get_lists() -> list[str]:
    return run_and_return(["show-lists"], mode="json")


def create_list(name: str):
    # List name uniqueness isn't required by Reminders.app, but it causes issues
    # when referring to lists as a simple string.
    if not list_exists(name):
        run_and_return(["new-list", name], mode="raw")

    # FIXME: return possibilities...
    # * list exists
    # *


def list_exists(name: str) -> bool:
    try:
        _ = get_tasks(name)
    except ListNotFoundException:
        return False

    return True


def run_and_return(
    cmd: list[str], mode: str = "raw", inject_reminder: bool = True
) -> list[str]:
    # Add reminders path to beginning of command
    if inject_reminder:
        cmd = [reminders()] + cmd

    if mode == "json":
        cmd = cmd + ["--format", "json"]

    try:
        result = run(cmd, capture_output=True, check=True, shell=False)
    except CalledProcessError as e:
        raise TaskCommandException(e)

    if mode == "raw":
        raw = result.stdout.decode("utf-8").splitlines()
        return raw
    elif mode == "json":
        json_output = result.stdout.decode("utf-8").strip()
        return json.loads(json_output)
    else:
        raise TaskException("invalid mode")


def reminders() -> str:
    reminders = which("reminders")
    if not reminders:
        raise TaskException("reminders-cli not found")
    return reminders


class TaskException(Exception):
    """Base Task Exception"""


class TaskCommandException(TaskException):
    """Command failure Exception"""

    def __init__(self, e: CalledProcessError) -> None:
        self.returncode = e.returncode
        self.cmd = " ".join(e.cmd)
        self.output = e.output.decode("utf-8").rstrip()
        self.stdout = e.stdout.decode("utf-8").rstrip()
        self.stderr = e.stderr.decode("utf-8").rstrip()

    def __str__(self) -> str:
        return f"'{self.cmd}' failed ({self.returncode}):\n{self.stderr}"


class ListNotFoundException(TaskException):
    """Task exception for when a list is not found"""
