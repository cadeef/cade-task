"""Command-line interface for Cade Task."""

from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich import print
from rich.console import Console
from rich.table import Table
from rich.text import Text

from .lib import (
    ListNotFoundException,
    ProjectCommentTask,
    TaskCommandException,
    TaskItem,
    TaskList,
    find_project_comment_tasks,
    get_lists,
    list_name_from_path,
    run_and_return,
)

PROJECT_DIR = Path.home() / "code"
APP_NAME = "cade_task"
app = typer.Typer(
    help=(
        "Manage macOS Reminders from the command line.\n\n"
        "By default, commands use the list inferred from your current project folder. "
        "Override it any time with --list."
    )
)
console = Console()
COMMENT_MARKERS = {
    "TODO",
    "FIXME",
    "ISSUE",
    "HACK",
    "TIP",
    "INFO",
    "PERF",
    "TEST",
    "WARN",
    "XXX",
    "BUG",
}


@dataclass(frozen=True, slots=True)
class DisplayTask:
    """A single row shown by the list command."""

    title: str
    location: str = ""
    index: int | None = None


def version_callback(value: bool) -> None:
    """Show the installed version and exit."""
    if value:
        print(importlib.metadata.version(APP_NAME))
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    project_dir: Annotated[
        str,
        typer.Option(
            "--project-dir",
            help=(
                "Root folder used to infer the active Reminders list from the current "
                "working directory. Can also be set with TASK_PROJECT_DIR."
            ),
            envvar="TASK_PROJECT_DIR",
        ),
    ] = str(PROJECT_DIR),
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Show the installed version and exit.",
        ),
    ] = None,
) -> None:
    """Configure shared CLI state before running a subcommand."""
    ctx.ensure_object(dict)
    ctx.obj["project"] = list_name_from_path(project_dir)


@app.command("list")
def list_(
    ctx: typer.Context,
    project: Annotated[
        Optional[str],
        typer.Option("--list", help="Use a specific Reminders list instead of the inferred one."),
    ] = None,
    todo: Annotated[
        bool,
        typer.Option("--todo", "-t", help="Show only incomplete tasks."),
    ] = False,
) -> None:
    """Show Reminders tasks and TODO-style comments from the current project."""
    selected_project = resolve_project(project, ctx.obj.get("project"))
    reminders_error: ListNotFoundException | None = None
    reminder_tasks: list[TaskItem] = []

    try:
        task_list = TaskList(selected_project)
        reminder_tasks = task_list.tasks()
    except ListNotFoundException as e:
        reminders_error = e

    if todo:
        reminder_tasks = [task for task in reminder_tasks if not task.is_complete]

    project_comment_tasks = find_project_comment_tasks()
    display_tasks = build_display_tasks(reminder_tasks, project_comment_tasks)

    if reminders_error and not project_comment_tasks:
        print(f":x: {reminders_error}")
        raise typer.Exit(code=1) from reminders_error

    if reminders_error and project_comment_tasks:
        print(f":warning: {reminders_error}. Showing project TODO comments instead.")

    print_tasks(display_tasks)


@app.command()
def lists(
    create: Annotated[
        Optional[str],
        typer.Option("--create", help="Create a new Reminders list with this name."),
    ] = None,
) -> None:
    """Show all Reminders lists, or create a new one."""
    if create:
        task_list = TaskList(create)
        task_list.create()
        print(f"List '{create}' created.")
        return

    print_lists(get_lists())


@app.command()
def add(
    ctx: typer.Context,
    title: Annotated[list[str], typer.Argument(help="Title of the task to create.")],
    project: Annotated[
        Optional[str],
        typer.Option("--list", help="Add the task to this Reminders list."),
    ] = None,
) -> None:
    """Create a new task."""
    selected_project = resolve_project(project, ctx.obj.get("project"))
    new_task = TaskItem(title=title, parent=selected_project).add()
    print(f":white_check_mark: Task '{new_task.title}' added to {new_task.parent}.")


@app.command()
def edit(
    ctx: typer.Context,
    index: Annotated[int, typer.Argument(help="Index of the task to rename.")],
    title: Annotated[list[str], typer.Argument(help="New title for the task.")],
    project: Annotated[
        Optional[str],
        typer.Option("--list", help="Edit a task in this Reminders list."),
    ] = None,
) -> None:
    """Rename a task by index."""
    selected_project = resolve_project(project, ctx.obj.get("project"))
    task = TaskItem(title=title, parent=selected_project, index=index)
    task.edit()
    print(f":white_check_mark: Task {index} modified to '{task.title}' in {task.parent}.")


@app.command()
def complete(
    ctx: typer.Context,
    tasks: Annotated[
        list[int],
        typer.Argument(help="One or more task indexes to mark complete."),
    ],
    project: Annotated[
        Optional[str],
        typer.Option("--list", help="Complete tasks in this Reminders list."),
    ] = None,
) -> None:
    """Mark one or more tasks complete."""
    selected_project = resolve_project(project, ctx.obj.get("project"))

    # Complete from highest to lowest index so earlier completions do not shift later indexes.
    for index in sorted(set(tasks), reverse=True):
        TaskItem(title="complete_task", parent=selected_project, index=index).complete()

    print(":white_check_mark: Task(s) completed.")


@app.command()
def open() -> None:
    """Open Reminders.app."""
    try:
        run_and_return(
            ["/usr/bin/open", "/System/Applications/Reminders.app/"],
            inject_reminder=False,
        )
    except TaskCommandException as e:
        print(f":x: Failed to open Reminders.app\n{e}")
        raise typer.Exit(code=1) from e


def resolve_project(explicit_project: str | None, inferred_project: str | None) -> str:
    """Choose the Reminders list to use for the current command."""
    project = explicit_project or inferred_project

    if not project:
        print(f":exclamation: Unable to determine list for {Path.cwd()}")
        raise typer.Exit(code=1)

    return project


def build_display_tasks(
    reminder_tasks: list[TaskItem],
    project_comment_tasks: list[ProjectCommentTask],
) -> list[DisplayTask]:
    """Build rows for the combined task list display."""
    display_tasks = [
        DisplayTask(
            title=str(task.title),
            index=index,
        )
        for index, task in enumerate(reminder_tasks)
    ]
    display_tasks.extend(
        DisplayTask(
            title=task.title,
            location=task.location,
        )
        for task in project_comment_tasks
    )
    return display_tasks


def print_tasks(tasks: list[DisplayTask]) -> None:
    """Render tasks as a Rich table."""
    if not tasks:
        print(":yawning_face: List empty.")
        return

    table = Table(
        title="Tasks",
        title_style="bold cyan",
        header_style="bold bright_white",
        border_style="blue",
    )
    table.add_column("Index", no_wrap=True, style="bold green")
    table.add_column("Task")

    for task in tasks:
        if task.index is not None:
            task_text = Text(task.title, style="bright_white")
        else:
            task_text = Text()
            marker, separator, remainder = task.title.partition(":")
            if separator and marker in COMMENT_MARKERS:
                task_text.append(f"{marker}:", style="bold cyan")
                if remainder:
                    task_text.append(remainder, style="yellow")
            else:
                task_text.append(task.title, style="yellow")
            if task.location:
                path, _, line_number = task.location.rpartition(":")
                if path and line_number:
                    task_text.append(" ")
                    task_text.append("(", style="dim white")
                    task_text.append(path, style="dim yellow")
                    task_text.append(":", style="yellow")
                    task_text.append(line_number, style="bold magenta")
                    task_text.append(")", style="dim white")
                else:
                    task_text.append(" ")
                    task_text.append(f"({task.location})", style="dim yellow")
        table.add_row(
            "" if task.index is None else str(task.index),
            task_text,
        )
    console.print(table)


def print_lists(lists_: list[str]) -> None:
    """Render Reminders list names as a Rich table."""
    table = Table(title="Lists", show_header=False)
    for list_name in lists_:
        table.add_row(list_name)
    console.print(table)


# Backward-compatible alias for code/tests that still import project_set.
project_set = resolve_project


if __name__ == "__main__":
    app()
