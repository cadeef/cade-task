"""Command-line interface for Cade Task."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path
from typing import Optional

import typer
from rich import print
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from .lib import (
    ListNotFoundException,
    TaskCommandException,
    TaskItem,
    TaskList,
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
    """Show tasks in a Reminders list."""
    selected_project = resolve_project(project, ctx.obj.get("project"))

    try:
        task_list = TaskList(selected_project)
        tasks = task_list.tasks()
    except ListNotFoundException as e:
        print(f":x: {e}")
        raise typer.Exit(code=1) from e

    if todo:
        tasks = [task for task in tasks if not task.is_complete]

    print_tasks(tasks)


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


def print_tasks(tasks: list[TaskItem]) -> None:
    """Render tasks as a Rich table."""
    if not tasks:
        print(":yawning_face: List empty.")
        return

    table = Table(title="Tasks", show_header=False)
    for index, task in enumerate(tasks):
        table.add_row(str(index), str(task.title))
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
