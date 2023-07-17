import json
import re
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError, run
from typing import List

PROJECT_DIR = Path(Path.home(), "code")


def list_resolve() -> str:
    match = re.search(rf"^{PROJECT_DIR}/([\w\-\.]+)/?", str(Path.cwd()), re.IGNORECASE)
    if match:
        project = match[1]
    # FIXME: Migrate all UX into cli
    # else:
    #     lists = get_lists()
    #     display_table(lists, ["List"], number_lines=True)
    #     display_title("Unknown list, select one.")
    #     n = click.prompt("List ID?", default=0, type=int)  # type: ignore[arg-type]

    #     try:
    #         project = lists[n]
    #     except IndexError:
    #         display_error(f"Selection '{n}' is invalid", exit=1)

    return project


def get_tasks(r_list: str) -> List[str]:
    try:
        tasks = run_and_return(["show", r_list], mode="json")
    except TaskCommandException as e:
        if "No reminders list matching" in e.output:
            raise ListNotFoundException(f"List '{r_list}' not found")
        else:
            raise TaskException(e)

    return tasks


def get_lists() -> List[str]:
    try:
        return run_and_return(["show-lists"], mode="json")
    except TaskCommandException as e:
        raise TaskException(e)


def run_and_return(cmd: List[str], mode="raw", inject_reminder=True) -> List[str]:
    # Add reminders path to beginning of command
    if inject_reminder:
        cmd = [reminders()] + cmd

    if mode == "json":
        cmd = cmd + ["--format", "json"]

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
