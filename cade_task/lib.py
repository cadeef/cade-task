import json
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError, run
from typing import Any

from devtools import debug  # noqa: F401


def list_name_from_path(project_dir: str, working_dir: str | None = None) -> str | None:
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

    # Strip off the first element of parts as project
    parts = project_dir_relative.parts
    if len(parts) >= 1:
        project = parts[0]

    return project


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


@dataclass
class TaskItem(object):
    """Reminder/task"""

    # {'externalId': 'CC7A70EB-0526-47AC-A4E3-D0EA5B2CF491',
    #   'isCompleted': False,
    #   'list': 'test',
    #   'priority': 0,
    #   'title': 'this is a magic test'},
    title: str
    parent: str
    id: str | None = None
    is_complete: bool | None = None
    priority: int | None = None
    index: int | None = None

    @staticmethod
    def from_dict(task: dict[str, Any]) -> "TaskItem":
        # Clean up naming convention
        rename_rules = {
            "externalId": "id",
            "isCompleted": "is_complete",
            "list": "parent",
        }

        for attribute in task.copy():
            if attribute in rename_rules:
                task[rename_rules[attribute]] = task.pop(attribute)

        return TaskItem(**task)

    def add(self):
        # Successful output: Added 'yet another test' to 'test'
        # FIXME: finish up when less tired
        # try:
        #     result = run_and_return(["add", self.parent, self.title])
        # except TaskCommandException as e:
        #     return False
        pass

    def complete(self):
        pass

    def edit(self):
        pass


@dataclass
class TaskList:
    """Reminders list object"""

    name: str

    def exists(self) -> bool:
        try:
            _ = self.tasks()
        except ListNotFoundException:
            return False

        return True

    def create(self):
        if not self.exists():
            run_and_return(["new-list", self.name], mode="raw")

    def tasks(self) -> list[TaskItem] | None:
        if hasattr(self, "_tasks"):
            return self._tasks  # type: ignore

        try:
            tasks = run_and_return(["show", self.name], mode="json")
        except TaskCommandException as e:
            if "No reminders list matching" in e.output:
                raise ListNotFoundException(f"List '{self.name}' not found")
            else:
                raise

        self._tasks = [TaskItem.from_dict(t) for t in tasks]  # type: ignore[arg-type]
        return self._tasks
