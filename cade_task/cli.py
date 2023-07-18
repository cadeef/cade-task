from pathlib import Path
from typing import List, Sequence

import click
from tablib import Dataset

from .lib import (  # isort:skip
    ListNotFoundException,
    TaskCommandException,
    get_lists,
    get_tasks,
    list_resolve,
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
    help="Base path for automatic directory-based list resolution",
)
@click.pass_context
def main(ctx, project_dir: str | None) -> None:
    if ctx.obj is None:
        ctx.obj = dict()

    project_dir = project_dir or str(PROJECT_DIR)
    ctx.obj["project"] = list_resolve(project_dir)


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
        tasks = [t["title"] for t in get_tasks(project)]  # type: ignore
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
        raise click.ClickException(e)


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
        click.echo(run_and_return(["add", project, t])[0])
    except TaskCommandException as e:
        raise click.ClickException(e)


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
            raise click.ClickException(e)


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
        raise click.ClickException(f"Command '{e.cmd}' failed with '{e.stderr}'")


def display_table(
    array: Sequence[str],
    # FIXME: Having a function called list wasn't a great idea, figure out re-naming so list[str]
    # can be used for consistency
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
