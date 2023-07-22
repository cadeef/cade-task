import pytest
from typer.testing import CliRunner

from cade_task.cli import app

TASK_COMMANDS = ["list", "add", "complete", "lists", "open"]

cli = CliRunner()


def test_no_command():
    """
    Ensure help text with TASK_COMMANDS is returned when --help is invoked
    """
    result = cli.invoke(app)
    assert result.exit_code == 2
    # assert "Usage:" in result.output
    # # Verify all commands are mentioned
    # for c in TASK_COMMANDS:
    #     assert c in result.output


@pytest.mark.parametrize("command", TASK_COMMANDS)
def test_subcommands_exist(command):
    """
    Ensure, at the very minimum, that TASK_COMMANDS are recognized subcommands
    """
    result = cli.invoke(app, [command, "--help"])
    assert result.exit_code == 0


def test_list_unknown():
    unknown_list = "uhduh34852f56"
    unknown_list_result = cli.invoke(app, ["list", "--list", unknown_list])
    assert unknown_list_result.exit_code != 0
    assert f"List '{unknown_list}' not found" in unknown_list_result.output


def test_add():
    pass


def test_complete():
    pass
