from pathlib import Path
from typing import List, Sequence

import click
from tablib import Dataset

from .lib import (
    ListNotFoundException,
    TaskCommandException,
    # TaskItem,
    TaskList,
    get_lists,
    list_name_from_path,
    run_and_return,
)

# Default
PROJECT_DIR = Path.home() / "code"


@click.group()
@click.option(
    "-d",
    "--project-dir",
    "project_dir",
    type=click.Path(exists=True),
    required=False,
    default=str(PROJECT_DIR),
    help="Base path for automatic directory-based list resolution",
)
@click.pass_context
def main(ctx, project_dir: str) -> None:
    ctx.ensure_object(dict)

    project = list_name_from_path(project_dir)

    # Create list if it is a project in project_dir and doesn't exist
    if project is not None:
        task_list = TaskList(project)
        if not task_list.exists():
            task_list.create()
            click.echo(f"INFO: Created list '{project}'")

    ctx.obj["project"] = project


@main.command()
@click.pass_context
@click.option("-l", "--list", "project", required=False)
def list(ctx, project: str | None = None) -> None:
    """
    List tasks for a given project
    """
    project = project or ctx.obj["project"]

    if not project:
        raise click.ClickException("Unable to determine list")

    display_title(project)
    try:
        task_list = TaskList(project)
        tasks = [t.title for t in task_list.tasks()]  # type: ignore
        display_table(tasks, ["Task"], number_lines=True)
    except ListNotFoundException:
        raise click.ClickException(f"List '{project}' not found")


@main.command()
def lists() -> None:
    """
    List all Reminders.app lists
    """
    try:
        display_table(get_lists(), ["List"], number_lines=False)
    except TaskCommandException as e:
        raise click.ClickException(e)  # type: ignore[arg-type]


@main.command()
@click.pass_context
@click.argument("task", nargs=-1)
@click.option("-l", "--list", "project", required=False)
def add(ctx, task: Sequence[str], project: str | None = None) -> None:
    """
    Add a task to a given project
    """
    project = project or ctx.obj["project"]

    if not project:
        raise click.ClickException("Unable to determine list")

    t = " ".join(str(i) for i in task)
    if not t:
        raise click.ClickException("No task specified, arborting")

    try:
        # task = TaskItem(t, project)
        # task.add()
        click.echo(run_and_return(["add", project, t])[0])
    except TaskCommandException as e:
        raise click.ClickException(e)  # type: ignore[arg-type]


@main.command()
@click.pass_context
@click.argument("tasks", nargs=-1)
@click.option("-l", "--list", "project", required=False)
def complete(ctx, tasks: Sequence[str], project: str | None = None) -> None:
    """
    Complete task(s) for a given project
    """
    if not project and not ctx.obj["project"]:
        raise click.ClickException("Unable to determine list")

    project = project or ctx.obj["project"]

    for t in sorted(tasks, reverse=True):
        try:
            click.echo(run_and_return(["complete", project, t])[0])
        except TaskCommandException as e:
            raise click.ClickException(e)  # type: ignore[arg-type]


@main.command()
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
        raise click.ClickException(e)  # type: ignore[arg-type]


def display_table(
    array: Sequence[str],
    # FIXME: Having a function called list wasn't a great idea, figure out re-naming
    # so list[str] can be used for consistency
    headers: List[str],
    number_lines=False,
    tablefmt: str = "fancy_grid",
) -> None:
    if len(array) == 0:
        raise click.ClickException("No results found")
    else:
        data = Dataset()
        data.headers = headers
        for t in array:
            data.append([t])

        click.echo(data.export("cli", showindex=number_lines, tablefmt=tablefmt))


def display_title(title: str) -> None:
    click.secho(f"{title}", fg="green", bold=True)


if __name__ == "__main__":
    main()
