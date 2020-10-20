import re
from pathlib import Path
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
# @click.argument("r_list", required=False)
@click.option("-l", "--list", "r_list", required=False)
def list(r_list: Optional[str] = None) -> None:
    """
    List tasks for a given project
    """
    r_list = r_list or list_resolve()
    display_title(r_list)
    display_table(get_tasks(r_list), ["Task"], number_lines=True)


@main.command()
def lists() -> None:
    """
    List all Reminders.app lists
    """
    display_table(get_lists(), ["List"], number_lines=True)


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

    click.echo(run_and_return([reminders(), "add", r_list, t])[0])


@main.command()
@click.argument("tasks", nargs=-1)
@click.option("-l", "--list", "r_list", required=False)
def complete(tasks: Sequence[str], r_list: Optional[str] = None) -> None:
    """
    Complete task(s) for a given project
    """
    r_list = r_list or list_resolve()

    for t in sorted(tasks, reverse=True):
        click.echo(run_and_return([reminders(), "complete", r_list, t])[0])


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
    run_and_return(["/usr/bin/open", "/System/Applications/Reminders.app/"])


def list_resolve() -> str:
    match = re.search(rf"^{PROJECT_DIR}/([\w\d\-]+)/?", str(Path.cwd()), re.IGNORECASE)
    if match:
        project = match[1]
    else:
        lists = get_lists()
        display_table(lists, ["List"], number_lines=True)
        display_title("Unknown list, select one.")
        n = click.prompt("List ID?", default="0", type=int)

        try:
            project = lists[n]
        except IndexError:
            display_error("Selection '{}' is invalid".format(n), exit=1)

    return project


def get_tasks(r_list: str) -> List[str]:
    tasks = run_and_return([reminders(), "show", r_list])
    # Strip off task numbers to make it more portable.
    # Yes we add them back for output occasionally.
    tasks = [re.sub(r"^[\d\s]+\s", "", t) for t in tasks]

    return tasks


def get_lists() -> List[str]:
    return run_and_return([reminders(), "show-lists"])


def run_and_return(cmd: Sequence[str], in_shell=False) -> List[str]:
    try:
        result = run(cmd, capture_output=True, check=True, shell=in_shell)
    except CalledProcessError as e:
        display_error(
            "Failed to execute {} (exit {}): {}".format(
                e.cmd, e.returncode, e.output.decode("utf-8").rstrip()
            ),
            exit=255,
        )

    output = result.stdout.decode("utf-8").splitlines()

    return output


def display_table(
    array: Sequence[str],
    headers: List[str],
    number_lines=False,
    tablefmt: str = "fancy_grid",
) -> None:
    if len(array) == 0:
        display_error("No results found")
    else:
        if number_lines:
            headers.insert(0, "ID")

        data = Dataset()
        data.headers = headers
        for i, t in enumerate(array):
            if number_lines:
                data.append([i, t])
            else:
                data.append([t])

        click.echo(data.export("cli", tablefmt=tablefmt))


def display_error(message: str, exit: Optional[int] = None) -> None:
    click.secho("ERROR: {}".format(message), fg="red")
    if exit:
        sys_exit(exit)


def display_title(title: str) -> None:
    click.secho("{}".format(title), fg="green", bold=True)


def reminders() -> str:
    return run_and_return(["which reminders"], in_shell=True)[0]


if __name__ == "__main__":
    main()
