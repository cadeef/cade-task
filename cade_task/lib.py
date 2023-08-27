import json
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError, run
from typing import Any

# from devtools import debug  # noqa: F401


class TaskItem(object):
    """Reminder/task"""

    def __init__(
        self,
        title: str | list,
        parent: str,
        task_id: str | None = None,
        is_complete: bool | None = None,
        priority: int | None = None,
        index: int | None = None,
        notes: str | None = None,
    ) -> None:
        if isinstance(title, list):
            self.title = " ".join(title)
        else:
            self.title = title

        self.parent = parent
        self.task_id = task_id
        self.is_complete = is_complete
        self.priority = priority
        self.index = index
        self.notes = notes

    @staticmethod
    def from_dict(task: dict[str, Any]) -> "TaskItem":
        # Clean up naming convention
        rename_rules = {
            "externalId": "task_id",
            "isCompleted": "is_complete",
            "list": "parent",
        }

        for attribute in task.copy():
            if attribute in rename_rules:
                task[rename_rules[attribute]] = task.pop(attribute)

        return TaskItem(**task)

    def add(self) -> "TaskItem":
        result = run_and_return(["add", self.parent, self.title], mode="json")
        task = TaskItem.from_dict(result.output)
        return task

    def complete(self):
        run_and_return(["complete", self.parent, self.index])

    def edit(self):
        run_and_return(["edit", self.parent, self.index, self.title], mode="raw")


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
            result = run_and_return(["show", self.name], mode="json")
            tasks = result.output
        except TaskCommandException as e:
            if "No reminders list matching" in e.output:
                raise ListNotFoundException(f"List '{self.name}' not found")
            else:
                raise

        self._tasks = [TaskItem.from_dict(t) for t in tasks]  # type: ignore[arg-type]
        return self._tasks


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

    # Set the first element of parts as project
    parts = project_dir_relative.parts
    if len(parts) >= 1:
        project = parts[0]

    return project


def get_lists() -> list[str]:
    result = run_and_return(["show-lists"], mode="json")
    return result.output


@dataclass
class RunAndReturnResult:
    command: str
    # FIXME: Unions, mypy, and I aren't friends
    # output: list[str | dict[str, Any]] | dict[str, Any]
    output: Any
    unmarshalled_output: bytes
    return_code: int


def run_and_return(
    cmd: list[str | Path | int], mode: str = "raw", inject_reminder: bool = True
) -> RunAndReturnResult:
    # Cast ints as str
    for i, v in enumerate(cmd.copy()):
        if isinstance(v, int):
            cmd[i] = str(v)

    # Add reminders path to beginning of command
    if inject_reminder:
        cmd = [reminders()] + cmd

    if mode == "json":
        cmd = cmd + ["--format", "json"]

    try:
        result = run(cmd, capture_output=True, check=True, shell=False)  # type: ignore[arg-type]  # noqa: E501
    except CalledProcessError as e:
        raise TaskCommandException(e)

    if mode == "raw":
        marshalled_result = result.stdout.decode("utf-8").splitlines()
    elif mode == "json":
        result_output = result.stdout.decode("utf-8").strip()
        marshalled_result = json.loads(result_output)
    else:
        raise TaskException("invalid mode")

    result_obj = RunAndReturnResult(
        command=" ".join(result.args),
        output=marshalled_result,
        unmarshalled_output=result.stdout,
        return_code=result.returncode,
    )
    return result_obj


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
