from pathlib import Path
from typing import Optional

import typer

# from devtools import debug  # noqa: F401
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

# Default
PROJECT_DIR = Path.home() / "code"

app = typer.Typer()


@app.callback()
def main(
    ctx: typer.Context,
    project_dir: str = typer.Option(
        default=str(PROJECT_DIR), envvar="TASK_PROJECT_DIR"
    ),
) -> None:
    ctx.ensure_object(dict)

    project = list_name_from_path(project_dir)

    # Create list if it is a project in project_dir and doesn't exist
    if project is not None:
        task_list = TaskList(project)
        if not task_list.exists():
            task_list.create()
            print(f":information_desk_person: Created list '{project}'.")

    ctx.obj["project"] = project


@app.command("list")
def list_(
    ctx: typer.Context, project: Annotated[Optional[str], typer.Option("--list")] = None
) -> None:
    """
    List tasks for a given project
    """
    project = project_set(project, ctx.obj["project"])

    try:
        task_list = TaskList(project)
        tasks = [t.title for t in task_list.tasks()]  # type: ignore
    except ListNotFoundException:
        print(f":x: List '{project}' not found")
        raise typer.Exit(code=1)

    if not tasks:
        print(":yawning_face: List empty.")
    else:
        table = Table(title="Tasks", show_header=False)

        for index, task in enumerate(tasks):
            table.add_row(str(index), task)

        Console().print(table)


@app.command()
def lists(create: Optional[str] = None) -> None:
    """
    List all Reminders.app lists
    """
    if create:
        task_list = TaskList(create)
        task_list.create()
        print(f"List '{create}' created.")
    else:
        lists = get_lists()
        table = Table(title="Lists", show_header=False)

        for list in lists:
            table.add_row(list)

        Console().print(table)


@app.command()
def add(
    ctx: typer.Context,
    title: list[str],
    project: Annotated[Optional[str], typer.Option("--list")] = None,
) -> None:
    """
    Add a task to a given project
    """
    project = project_set(project, ctx.obj["project"])
    title_str = " ".join(title)
    task = TaskItem(title_str, project)
    task.add()
    print(f"Task '{title_str}' added to {project}.")


@app.command()
def complete(
    ctx: typer.Context,
    tasks: list[str],
    project: Annotated[Optional[str], typer.Option("--list")] = None,
) -> None:
    """
    Complete task(s) for a given project
    """
    project = project_set(project, ctx.obj["project"])

    for t in sorted(tasks, reverse=True):
        # FIXME: setting a dummy title is inelegant
        task = TaskItem(title="complete_task", parent=project, index=int(t))
        task.complete()

    print("Task(s) completed.")


@app.command()
def open() -> None:
    """
    Open Reminders.app or move it to the foreground
    """
    try:
        run_and_return(
            ["/usr/bin/open", "/System/Applications/Reminders.app/"],
            inject_reminder=False,
        )
    except TaskCommandException as e:
        print(f":x: Failed to open Reminders.app\n{e}")
        raise typer.Exit(code=1)


def project_set(first: str | None, second: str) -> str:
    # This is dumb, but I wanted it out of the way without thinking more than function
    project = first or second

    if not project:
        print(":exclamation: Unable to determine list")
        raise typer.Exit(code=1)

    return project


if __name__ == "__main__":
    app()
