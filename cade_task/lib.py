"""Core objects and helpers for interacting with macOS Reminders via reminders-cli."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError, run
from typing import Any, Literal

RunMode = Literal["raw", "json"]
CommandPart = str | Path | int

_RENAME_RULES: dict[str, str] = {
    "externalId": "task_id",
    "isCompleted": "is_complete",
    "dueDate": "due_date",
    "startDate": "start_date",
    "list": "parent",
}
_COMMENT_MARKER_RE = re.compile(r"\b(TODO|FIXME|ISSUE|HACK|TIP|INFO|PERF|TEST|WARN|XXX|BUG):(.*)")
_SKIPPED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
}
_MAX_SCAN_BYTES = 1_000_000


@dataclass
class TaskItem:
    """A single reminder/task returned by or sent to reminders-cli."""

    title: str | list[str]
    parent: str
    task_id: str | None = None
    is_complete: bool | None = None
    priority: int | None = None
    index: int | None = None
    notes: str | None = None
    due_date: str | None = None  # TODO: Convert to datetime.
    start_date: str | None = None  # TODO: Convert to datetime.

    def __post_init__(self) -> None:
        """Normalize user-provided title input.

        Inputs:
            self.title: Either a string title or a list of words from the CLI.

        Outputs:
            None. Stores the normalized title on self as a string so later
            command calls always receive a string.
        """
        self.title = " ".join(self.title) if isinstance(self.title, list) else self.title

    @classmethod
    def from_dict(cls, task: dict[str, Any]) -> "TaskItem":
        """Create a TaskItem from reminders-cli JSON output.

        Inputs:
            task: A dictionary from reminders-cli, using its original field names.

        Outputs:
            A TaskItem with CLI field names converted to Python-friendly names.
        """
        renamed = {_RENAME_RULES.get(key, key): value for key, value in task.items()}
        return cls(**renamed)

    def add(self) -> "TaskItem":
        """Add this task to its parent Reminders list.

        Inputs:
            self.parent: Name of the Reminders list to add to.
            self.title: Title of the task to create.

        Outputs:
            The created TaskItem returned by reminders-cli.
        """
        result = run_and_return(["add", self.parent, self._title_text()], mode="json")
        return TaskItem.from_dict(result.output)

    def complete(self) -> None:
        """Mark this task complete by list name and index.

        Inputs:
            self.parent: Name of the Reminders list that contains the task.
            self.index: Numeric task index in that list.

        Outputs:
            None. Raises TaskException if the task has no index.
        """
        run_and_return(["complete", self.parent, str(self._required_index())])

    def edit(self) -> None:
        """Rename this task by list name and index.

        Inputs:
            self.parent: Name of the Reminders list that contains the task.
            self.index: Numeric task index in that list.
            self.title: New title for the task.

        Outputs:
            None. Raises TaskException if the task has no index.
        """
        run_and_return(["edit", self.parent, self._required_index(), self._title_text()])

    def _title_text(self) -> str:
        """Return the task title as a guaranteed string."""
        return " ".join(self.title) if isinstance(self.title, list) else self.title

    def _required_index(self) -> int:
        """Return the task index or fail with a clear error.

        Inputs:
            self.index: Optional task index.

        Outputs:
            The task index as an integer.
        """
        if self.index is None:
            raise TaskException(f"Task '{self._title_text()}' does not have an index.")
        return self.index


@dataclass
class TaskList:
    """A Reminders list and cached access to its tasks."""

    name: str
    _tasks: list[TaskItem] | None = field(default=None, init=False, repr=False)

    def exists(self) -> bool:
        """Check whether this Reminders list currently exists.

        Inputs:
            self.name: Name of the Reminders list to look for.

        Outputs:
            True when a matching list exists, otherwise False.
        """
        return self.name in get_lists()

    def create(self) -> None:
        """Create this Reminders list if it does not already exist.

        Inputs:
            self.name: Name of the list to create.

        Outputs:
            None. Raises TaskException when the list already exists.
        """
        # Reminders.app allows duplicate list names, but reminders-cli does not expose
        # stable list IDs here, so avoid creating duplicate names from this app.
        if self.exists():
            raise TaskException(f"List '{self.name}' already exists.")
        run_and_return(["new-list", self.name], mode="raw")
        self.clear_cache()

    def tasks(self, *, refresh: bool = False) -> list[TaskItem]:
        """Return tasks from this Reminders list.

        Inputs:
            refresh: When True, ignore any cached tasks and fetch fresh data.

        Outputs:
            A list of TaskItem objects.
        """
        if self._tasks is not None and not refresh:
            return self._tasks

        try:
            result = run_and_return(["show", self.name], mode="json")
        except TaskCommandException as e:
            if "No reminders list matching" in e.output:
                raise ListNotFoundException(f"List '{self.name}' not found") from e
            raise

        self._tasks = [TaskItem.from_dict(task) for task in result.output]
        return self._tasks

    def clear_cache(self) -> None:
        """Discard cached tasks for this list.

        Inputs:
            None.

        Outputs:
            None. The next tasks() call will fetch fresh data.
        """
        self._tasks = None


@dataclass(frozen=True, slots=True)
class ProjectCommentTask:
    """A TODO-style comment discovered in a project file."""

    title: str
    path: str
    line_number: int

    @property
    def location(self) -> str:
        """Return the display location for the comment."""
        return f"{self.path}:{self.line_number}"


def find_project_comment_tasks(working_dir: str | Path | None = None) -> list[ProjectCommentTask]:
    """Scan the working directory for TODO-style comments in project files."""
    root = Path(working_dir).expanduser().resolve() if working_dir else Path.cwd().resolve()
    matches: list[ProjectCommentTask] = []

    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            directory for directory in dirnames if directory not in _SKIPPED_DIRS and not directory.startswith(".")
        )

        for filename in sorted(filenames):
            if filename.startswith("."):
                continue

            file_path = Path(current_root) / filename

            try:
                if file_path.stat().st_size > _MAX_SCAN_BYTES:
                    continue
                contents = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            if "\x00" in contents:
                continue

            relative_path = file_path.relative_to(root)
            for line_number, line in enumerate(contents.splitlines(), start=1):
                match = _COMMENT_MARKER_RE.search(line)
                if not match:
                    continue

                title = match.group(0).strip()
                matches.append(
                    ProjectCommentTask(
                        title=title,
                        path=str(relative_path),
                        line_number=line_number,
                    )
                )

    return matches


def list_name_from_path(project_dir: str | Path, working_dir: str | Path | None = None) -> str | None:
    """Infer the Reminders list name from the current project path.

    Inputs:
        project_dir: Root directory where project folders live.
        working_dir: Directory to inspect. Defaults to the current working directory.

    Outputs:
        The first path component under project_dir, or None when outside project_dir.
    """
    project_root = Path(project_dir).expanduser().resolve()
    cwd = Path(working_dir).expanduser().resolve() if working_dir else Path.cwd().resolve()

    try:
        relative = cwd.relative_to(project_root)
    except ValueError:
        return None

    return relative.parts[0] if relative.parts else None


def get_lists() -> list[str]:
    """Fetch all Reminders list names.

    Inputs:
        None.

    Outputs:
        A list of Reminders list names returned by reminders-cli.
    """
    result = run_and_return(["show-lists"], mode="json")
    return result.output


def reminders() -> str:
    """Find the reminders-cli executable.

    Inputs:
        None.

    Outputs:
        Absolute path to the reminders executable.
    """
    path = which("reminders")
    if not path:
        raise TaskException("'reminders' from reminders-cli not found in PATH.")
    return path


@dataclass(slots=True)
class RunAndReturnResult:
    """Structured result from a command executed by run_and_return."""

    command: str
    output: Any
    unmarshalled_output: bytes
    return_code: int


def run_and_return(
    cmd: list[CommandPart],
    mode: RunMode = "raw",
    inject_reminder: bool = True,
) -> RunAndReturnResult:
    """Run a command and parse its output consistently.

    Inputs:
        cmd: Command arguments. By default these are appended after reminders-cli.
        mode: "raw" returns stdout lines; "json" parses stdout as JSON.
        inject_reminder: When True, prepend the reminders-cli executable path.

    Outputs:
        RunAndReturnResult containing command text, parsed output, raw stdout bytes,
        and return code.
    """
    args = [str(part) for part in cmd]

    if inject_reminder:
        args = [reminders(), *args]

    if mode == "json":
        args.extend(["--format", "json"])

    try:
        result = run(args, capture_output=True, check=True, shell=False)
    except CalledProcessError as e:
        raise TaskCommandException(e) from e

    stdout = result.stdout.decode()
    if mode == "raw":
        output = stdout.splitlines()
    elif mode == "json":
        try:
            output = json.loads(stdout.strip())
        except json.JSONDecodeError as e:
            raise TaskException(f"Command returned invalid JSON: {' '.join(args)}") from e
    else:
        # This is mostly defensive because the RunMode type already restricts callers.
        raise TaskException(f"Invalid mode: {mode!r}")

    return RunAndReturnResult(
        command=" ".join(args),
        output=output,
        unmarshalled_output=result.stdout,
        return_code=result.returncode,
    )


class TaskException(Exception):
    """Base exception for predictable app-level failures.

    Inputs:
        Standard Exception arguments.

    Outputs:
        An exception instance that callers can catch for task app errors.
    """


class TaskCommandException(TaskException):
    """Error raised when an external command returns a non-zero exit code."""

    def __init__(self, e: CalledProcessError) -> None:
        """Capture useful details from a failed subprocess call.

        Inputs:
            e: The CalledProcessError raised by subprocess.run.

        Outputs:
            None. Stores return code, command, stdout, and stderr on the instance.
        """
        self.returncode = e.returncode
        self.cmd = " ".join(str(part) for part in e.cmd)
        self.output = (e.output or b"").decode().strip()
        self.stdout = (e.stdout or b"").decode().strip()
        self.stderr = (e.stderr or b"").decode().strip()

    def __str__(self) -> str:
        """Format the command failure for CLI display.

        Inputs:
            None.

        Outputs:
            A readable error message string.
        """
        details = self.stderr or self.stdout or self.output or "No output captured."
        return f"'{self.cmd}' failed ({self.returncode}):\n{details}"


class ListNotFoundException(TaskException):
    """Error raised when a requested Reminders list cannot be found.

    Inputs:
        Standard Exception arguments.

    Outputs:
        An exception instance for missing-list failures.
    """
