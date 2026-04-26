"""Unit tests for cade_task.cli.

These tests exercise the Typer CLI while replacing all Reminders.app/reminders-cli
interactions with test doubles. They should be safe to run on any machine.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

import pytest
import typer
from typer.testing import CliRunner

from cade_task import cli
from cade_task.lib import ListNotFoundException, ProjectCommentTask, TaskCommandException

runner = CliRunner()


class FakeTask:
    """Small TaskItem stand-in used by list output tests."""

    def __init__(self, title: str, is_complete: bool | None = None) -> None:
        self.title = title
        self.is_complete = is_complete


class FakeTaskListState(TypedDict):
    """Mutable state used by a generated FakeTaskList class."""

    created_lists: list[str]
    tasks_by_list: dict[str, list[FakeTask]]
    list_not_found: set[str]


TaskListFactory = Callable[..., tuple[type, FakeTaskListState]]


@pytest.fixture
def fake_task_list_factory() -> TaskListFactory:
    """Create isolated TaskList fakes without mutable class defaults."""

    def factory(
        *,
        tasks_by_list: dict[str, list[FakeTask]] | None = None,
        list_not_found: set[str] | None = None,
    ) -> tuple[type, FakeTaskListState]:
        state: FakeTaskListState = {
            "created_lists": [],
            "tasks_by_list": tasks_by_list or {},
            "list_not_found": list_not_found or set(),
        }

        class FakeTaskList:
            """TaskList stand-in scoped to a single test."""

            def __init__(self, name: str) -> None:
                self.name = name

            def create(self) -> None:
                state["created_lists"].append(self.name)

            def tasks(self) -> list[FakeTask]:
                if self.name in state["list_not_found"]:
                    raise ListNotFoundException(f"List '{self.name}' not found")
                return state["tasks_by_list"].get(self.name, [])

        return FakeTaskList, state

    return factory


@pytest.fixture
def inferred_project(monkeypatch: pytest.MonkeyPatch) -> str:
    """Make the callback infer a predictable list name."""
    monkeypatch.setattr(cli, "list_name_from_path", lambda project_dir: "Work")
    return "Work"


# ---------------------------------------------------------------------------
# Callback/version behavior
# ---------------------------------------------------------------------------


def test_version_option_prints_package_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """The eager --version flag prints the package version and exits successfully."""
    monkeypatch.setattr(cli.importlib.metadata, "version", lambda app_name: "1.2.3")

    result = runner.invoke(cli.app, ["--version"])

    assert result.exit_code == 0
    assert "1.2.3" in result.output


def test_callback_stores_inferred_project(monkeypatch: pytest.MonkeyPatch) -> None:
    """The callback stores the project inferred from the configured project dir."""
    seen_project: dict[str, str | None] = {}

    def fake_command(ctx: typer.Context) -> None:
        seen_project["value"] = ctx.obj["project"]

    monkeypatch.setattr(cli, "list_name_from_path", lambda project_dir: "Inferred")
    test_app = typer.Typer()
    test_app.callback()(cli.main)
    test_app.command("probe")(fake_command)

    result = runner.invoke(test_app, ["probe"])

    assert result.exit_code == 0
    assert seen_project["value"] == "Inferred"


def test_root_help_includes_project_inference_guidance() -> None:
    """`--help` explains how the CLI chooses a Reminders list."""
    result = runner.invoke(cli.app, ["--help"])

    assert result.exit_code == 0
    assert "Manage macOS Reminders from the command line." in result.output
    assert "Override it any time with --list." in result.output
    assert "--project-dir" in result.output


def test_add_help_describes_title_argument_and_list_override() -> None:
    """`add --help` explains the title argument and list selection."""
    result = runner.invoke(cli.app, ["add", "--help"])

    assert result.exit_code == 0
    assert "Create a new task." in result.output
    assert "Title of the task to create." in result.output
    assert "Add the task to this Reminders list." in result.output


# ---------------------------------------------------------------------------
# list command
# ---------------------------------------------------------------------------


def test_list_command_prints_tasks(
    monkeypatch: pytest.MonkeyPatch,
    inferred_project: str,
    fake_task_list_factory: TaskListFactory,
) -> None:
    """`list` prints tasks from the inferred Reminders list."""
    fake_task_list, _ = fake_task_list_factory(
        tasks_by_list={inferred_project: [FakeTask("Write tests"), FakeTask("Ship")]},
    )
    monkeypatch.setattr(cli, "TaskList", fake_task_list)
    monkeypatch.setattr(cli, "find_project_comment_tasks", lambda: [])

    result = runner.invoke(cli.app, ["list"])

    assert result.exit_code == 0
    assert "Tasks" in result.output
    assert "Write tests" in result.output
    assert "Ship" in result.output


def test_list_command_uses_explicit_list(
    monkeypatch: pytest.MonkeyPatch,
    fake_task_list_factory: TaskListFactory,
) -> None:
    """`list --list NAME` takes precedence over an inferred project."""
    monkeypatch.setattr(cli, "list_name_from_path", lambda project_dir: "Inferred")
    fake_task_list, _ = fake_task_list_factory(
        tasks_by_list={"Personal": [FakeTask("Pay bill")]},
    )
    monkeypatch.setattr(cli, "TaskList", fake_task_list)
    monkeypatch.setattr(cli, "find_project_comment_tasks", lambda: [])

    result = runner.invoke(cli.app, ["list", "--list", "Personal"])

    assert result.exit_code == 0
    assert "Pay bill" in result.output


def test_list_command_filters_completed_tasks_when_todo_is_set(
    monkeypatch: pytest.MonkeyPatch,
    inferred_project: str,
    fake_task_list_factory: TaskListFactory,
) -> None:
    """`list --todo` hides tasks that are already complete."""
    fake_task_list, _ = fake_task_list_factory(
        tasks_by_list={
            inferred_project: [
                FakeTask("Open task", is_complete=False),
                FakeTask("Completed task", is_complete=True),
                FakeTask("Unknown status", is_complete=None),
            ],
        },
    )
    monkeypatch.setattr(cli, "TaskList", fake_task_list)
    monkeypatch.setattr(cli, "find_project_comment_tasks", lambda: [])

    result = runner.invoke(cli.app, ["list", "--todo"])

    assert result.exit_code == 0
    assert "Open task" in result.output
    assert "Unknown status" in result.output
    assert "Completed task" not in result.output


def test_list_command_prints_empty_message(
    monkeypatch: pytest.MonkeyPatch,
    inferred_project: str,
    fake_task_list_factory: TaskListFactory,
) -> None:
    """`list` prints a friendly message when the selected list has no tasks."""
    fake_task_list, _ = fake_task_list_factory(tasks_by_list={inferred_project: []})
    monkeypatch.setattr(cli, "TaskList", fake_task_list)
    monkeypatch.setattr(cli, "find_project_comment_tasks", lambda: [])

    result = runner.invoke(cli.app, ["list"])

    assert result.exit_code == 0
    assert "List empty" in result.output


def test_list_command_exits_when_list_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    inferred_project: str,
    fake_task_list_factory: TaskListFactory,
) -> None:
    """`list` exits with code 1 when the Reminders list cannot be found."""
    fake_task_list, _ = fake_task_list_factory(list_not_found={inferred_project})
    monkeypatch.setattr(cli, "TaskList", fake_task_list)
    monkeypatch.setattr(cli, "find_project_comment_tasks", lambda: [])

    result = runner.invoke(cli.app, ["list"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_list_command_includes_project_comment_tasks(
    monkeypatch: pytest.MonkeyPatch,
    inferred_project: str,
    fake_task_list_factory: TaskListFactory,
) -> None:
    """`list` shows TODO-style project comments after Reminders tasks."""
    fake_task_list, _ = fake_task_list_factory(
        tasks_by_list={inferred_project: [FakeTask("Write tests")]},
    )
    monkeypatch.setattr(cli, "TaskList", fake_task_list)
    monkeypatch.setattr(
        cli,
        "find_project_comment_tasks",
        lambda: [ProjectCommentTask(title="TODO: remove debug print", path="src/app.py", line_number=12)],
    )

    result = runner.invoke(cli.app, ["list"])

    assert result.exit_code == 0
    assert "Write tests" in result.output
    assert "TODO: remove debug print" in result.output
    assert "src/app.py:12" in result.output


def test_list_command_uses_project_comments_when_list_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    inferred_project: str,
    fake_task_list_factory: TaskListFactory,
) -> None:
    """`list` falls back to project comments when the Reminders list is missing."""
    fake_task_list, _ = fake_task_list_factory(list_not_found={inferred_project})
    monkeypatch.setattr(cli, "TaskList", fake_task_list)
    monkeypatch.setattr(
        cli,
        "find_project_comment_tasks",
        lambda: [ProjectCommentTask(title="FIXME: handle edge case", path="cli.py", line_number=7)],
    )

    result = runner.invoke(cli.app, ["list"])

    assert result.exit_code == 0
    assert "not found" in result.output
    assert "Showing project TODO comments instead." in result.output
    assert "FIXME: handle edge case" in result.output


# ---------------------------------------------------------------------------
# lists command
# ---------------------------------------------------------------------------


def test_lists_command_prints_all_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    """`lists` prints all Reminders list names returned by the library."""
    monkeypatch.setattr(cli, "get_lists", lambda: ["Work", "Personal"])

    result = runner.invoke(cli.app, ["lists"])

    assert result.exit_code == 0
    assert "Lists" in result.output
    assert "Work" in result.output
    assert "Personal" in result.output


def test_lists_command_can_create_list(
    monkeypatch: pytest.MonkeyPatch,
    fake_task_list_factory: TaskListFactory,
) -> None:
    """`lists --create NAME` creates the given Reminders list."""
    fake_task_list, state = fake_task_list_factory()
    monkeypatch.setattr(cli, "TaskList", fake_task_list)

    result = runner.invoke(cli.app, ["lists", "--create", "NewList"])

    assert result.exit_code == 0
    assert "NewList" in state["created_lists"]
    assert "created" in result.output


# ---------------------------------------------------------------------------
# add/edit/complete commands
# ---------------------------------------------------------------------------


def test_add_command_creates_task_in_selected_list(
    monkeypatch: pytest.MonkeyPatch,
    inferred_project: str,
) -> None:
    """`add` builds a TaskItem, adds it, and prints the created task."""
    created: dict[str, Any] = {}

    class FakeTaskItem:
        def __init__(self, title: list[str] | str, parent: str, index: int | None = None) -> None:
            created["title"] = title
            created["parent"] = parent
            created["index"] = index

        def add(self) -> Any:
            return type("AddedTask", (), {"title": "Buy milk", "parent": inferred_project})()

    monkeypatch.setattr(cli, "TaskItem", FakeTaskItem)

    result = runner.invoke(cli.app, ["add", "Buy", "milk"])

    assert result.exit_code == 0
    assert created == {"title": ["Buy", "milk"], "parent": inferred_project, "index": None}
    assert "Buy milk" in result.output
    assert inferred_project in result.output


def test_edit_command_renames_task(
    monkeypatch: pytest.MonkeyPatch,
    inferred_project: str,
) -> None:
    """`edit` passes the selected index and replacement title to TaskItem.edit()."""
    edited: dict[str, Any] = {}

    class FakeTaskItem:
        def __init__(self, title: list[str] | str, parent: str, index: int | None = None) -> None:
            self.title = " ".join(title) if isinstance(title, list) else title
            self.parent = parent
            self.index = index
            edited["title"] = title
            edited["parent"] = parent
            edited["index"] = index

        def edit(self) -> None:
            edited["called"] = True

    monkeypatch.setattr(cli, "TaskItem", FakeTaskItem)

    result = runner.invoke(cli.app, ["edit", "2", "Updated", "title"])

    assert result.exit_code == 0
    assert edited == {
        "title": ["Updated", "title"],
        "parent": inferred_project,
        "index": 2,
        "called": True,
    }
    assert "Task 2 modified" in result.output


def test_complete_command_deduplicates_and_sorts_descending(
    monkeypatch: pytest.MonkeyPatch,
    inferred_project: str,
) -> None:
    """`complete` handles duplicate indexes once and completes from high to low."""
    completed_indexes: list[int | None] = []

    class FakeTaskItem:
        def __init__(self, title: str, parent: str, index: int | None = None) -> None:
            self.title = title
            self.parent = parent
            self.index = index

        def complete(self) -> None:
            completed_indexes.append(self.index)

    monkeypatch.setattr(cli, "TaskItem", FakeTaskItem)

    result = runner.invoke(cli.app, ["complete", "1", "3", "1", "2"])

    assert result.exit_code == 0
    assert completed_indexes == [3, 2, 1]
    assert "completed" in result.output


# ---------------------------------------------------------------------------
# open command
# ---------------------------------------------------------------------------


def test_open_command_invokes_macos_open(monkeypatch: pytest.MonkeyPatch) -> None:
    """`open` delegates to /usr/bin/open without injecting reminders-cli."""
    call_args: dict[str, Any] = {}

    def fake_run_and_return(cmd: list[str], inject_reminder: bool = True) -> None:
        call_args["cmd"] = cmd
        call_args["inject_reminder"] = inject_reminder

    monkeypatch.setattr(cli, "run_and_return", fake_run_and_return)

    result = runner.invoke(cli.app, ["open"])

    assert result.exit_code == 0
    assert call_args == {
        "cmd": ["/usr/bin/open", "/System/Applications/Reminders.app/"],
        "inject_reminder": False,
    }


def test_open_command_exits_when_open_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """`open` exits with code 1 when the underlying command fails."""
    err = TaskCommandException.__new__(TaskCommandException)
    err.returncode = 1
    err.cmd = "/usr/bin/open /System/Applications/Reminders.app/"
    err.output = ""
    err.stdout = ""
    err.stderr = "failed to open"

    def fake_run_and_return(cmd: list[str], inject_reminder: bool = True) -> None:
        raise err

    monkeypatch.setattr(cli, "run_and_return", fake_run_and_return)

    result = runner.invoke(cli.app, ["open"])

    assert result.exit_code == 1
    assert "Failed to open Reminders.app" in result.output


# ---------------------------------------------------------------------------
# resolve_project / backward-compatible alias
# ---------------------------------------------------------------------------


def test_resolve_project_prefers_explicit_project() -> None:
    """resolve_project returns the explicit project before the inferred one."""
    assert cli.resolve_project("Explicit", "Inferred") == "Explicit"


def test_resolve_project_falls_back_to_inferred_project() -> None:
    """resolve_project returns the inferred project when no explicit value is given."""
    assert cli.resolve_project(None, "Inferred") == "Inferred"


def test_resolve_project_exits_when_no_project_is_available() -> None:
    """resolve_project exits with code 1 when neither source provides a list name."""
    with pytest.raises(typer.Exit) as exc_info:
        cli.resolve_project(None, None)

    assert exc_info.value.exit_code == 1


def test_project_set_alias_points_to_resolve_project() -> None:
    """project_set remains available for older callers/tests."""
    assert cli.project_set is cli.resolve_project
