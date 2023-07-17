import json
import re
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError, run
from sys import exit as sys_exit
from typing import List, Optional, Sequence

import click
from tablib import Dataset

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
    except ListNotFoundException as e:
        display_error(str(e), exit=255)


@main.command()
def lists() -> None:
    """
    List all Reminders.app lists
    """
    try:
        display_table(get_lists(), ["List"], number_lines=True)
    except TaskCommandException as e:
        display_error(str(e), exit=1)


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
        display_error("No task specified, arborting", exit=1)

    try:
        click.echo(run_and_return([reminders(), "add", r_list, t])[0])
    except TaskCommandException as e:
        display_error(str(e), exit=1)


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
            click.echo(run_and_return([reminders(), "complete", r_list, t])[0])
        except TaskCommandException as e:
            display_error(str(e), exit=1)


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
        run_and_return(["/usr/bin/open", "/System/Applications/Reminders.app/"])
    except TaskCommandException as e:
        display_error(f"Command '{e.cmd}' failed with '{e.stderr}'", exit=255)


def list_resolve() -> str:
    match = re.search(rf"^{PROJECT_DIR}/([\w\-\.]+)/?", str(Path.cwd()), re.IGNORECASE)
    if match:
        project = match[1]
    else:
        lists = get_lists()
        display_table(lists, ["List"], number_lines=True)
        display_title("Unknown list, select one.")
        n = click.prompt("List ID?", default=0, type=int)  # type: ignore[arg-type]

        try:
            project = lists[n]
        except IndexError:
            display_error(f"Selection '{n}' is invalid", exit=1)

    return project


def get_tasks(r_list: str) -> List[str]:
    try:
        tasks = run_and_return(
            [reminders(), "show", "--format", "json", r_list], mode="json"
        )
    except TaskCommandException as e:
        if "No reminders list matching" in e.output:
            raise ListNotFoundException(f"List '{r_list}' not found")
        else:
            raise TaskException(e)

    return tasks


def get_lists() -> List[str]:
    try:
        return run_and_return(
            [reminders(), "show-lists", "--format", "json"], mode="json"
        )
    except TaskCommandException as e:
        raise TaskException(e)


def run_and_return(cmd: Sequence[str], mode="raw") -> List[str]:
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


def display_table(
    array: Sequence[str],
    headers: List[str],
    number_lines=False,
    tablefmt: str = "fancy_grid",
) -> None:
    if len(array) == 0:
        display_error("No results found")
    else:
        data = Dataset()
        data.headers = headers
        for t in array:
            data.append([t])

        click.echo(data.export("cli", showindex=number_lines, tablefmt=tablefmt))


def display_error(message: str, exit: Optional[int] = None) -> None:
    click.secho(f"ERROR: {message}", fg="red")
    if exit:
        sys_exit(exit)


def display_title(title: str) -> None:
    click.secho(f"{title}", fg="green", bold=True)


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


class ListNotFoundException(TaskException):
    """Task exception for when a list is not found"""


if __name__ == "__main__":
    main()
