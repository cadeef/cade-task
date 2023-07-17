from pathlib import Path
from typing import List, Optional, Sequence

import click
from tablib import Dataset

from .lib import (
    ListNotFoundException,
    TaskCommandException,
    get_lists,
    get_tasks,
    list_resolve,
    run_and_return,
)

PROJECT_DIR = Path(Path.home(), "code")


@click.group()
# @click.option("-d", "--project-dir", "project-dir", required=False)
def main() -> None:
    pass


@main.command()
@click.option("-l", "--list", "r_list", required=False)
def list(r_list: Optional[str] = None) -> None:
    """
    List tasks for a given project
    """
    r_list = r_list or list_resolve()
    display_title(r_list)

    try:
        tasks = [t["title"] for t in get_tasks(r_list)]  # type: ignore
        display_table(tasks, ["Task"], number_lines=True)
    except ListNotFoundException:
        raise click.BadParameter("List not found", param_hint="--list")


@main.command()
def lists() -> None:
    """
    List all Reminders.app lists
    """
    try:
        display_table(get_lists(), ["List"], number_lines=True)
    except TaskCommandException as e:
        raise click.ClickException(e)


@main.command()
@click.argument("task", nargs=-1)
@click.option("-l", "--list", "r_list", required=False)
def add(task: Sequence[str], r_list: Optional[str] = None) -> None:
    """
    Add a task to a given project
    """
    r_list = r_list or list_resolve()
    t = " ".join(str(i) for i in task)
    if not t:
        raise click.ClickException("No task specified, arborting")

    try:
        click.echo(run_and_return(["add", r_list, t])[0])
    except TaskCommandException as e:
        raise click.ClickException(e)


@main.command()
@click.argument("tasks", nargs=-1)
@click.option("-l", "--list", "r_list", required=False)
def complete(tasks: Sequence[str], r_list: Optional[str] = None) -> None:
    """
    Complete task(s) for a given project
    """
    r_list = r_list or list_resolve()

    for t in sorted(tasks, reverse=True):
        try:
            click.echo(run_and_return(["complete", r_list, t])[0])
        except TaskCommandException as e:
            raise click.ClickException(e)


@main.command()
@click.option(
    "-u", "--user", required=False, help="user to match, i.e. 'FIXME(<user>):'"
)
def sync(user: Optional[str] = None) -> None:
    """
    Synchronize TODO|FIXME code comments to and from Reminders.app
    """

    # TODO: Add automagic syncing of TODO|FIXME|WHATEVER to project lists
    pass


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
