import pytest
from click.testing import CliRunner

import cade_task.cli

TASK_COMMANDS = ["list", "lists", "add", "complete", "sync", "open"]

@pytest.fixture
def cli():
    """
    Returns an instance of click.testing.CliRunner
    """
    return CliRunner()

def test_no_command(cli):
    """
    Ensure help text with TASK_COMMANDS is returned when --help is invoked
    """
    result = cli.invoke(cade_task.cli.main)
    assert result.exit_code == 0
    assert "Usage:" in result.output
    # Verify all commands are mentioned
    for c in TASK_COMMANDS:
        assert c in result.output

@pytest.mark.parametrize("command", TASK_COMMANDS)
def test_subcommands_exist(cli, command):
    """
    Ensure, at the very minimum, that TASK_COMMANDS are recognized subcommands
    """
    result = cli.invoke(cade_task.cli.main, [command, "--help"])
    assert result.exit_code == 0

def test_subcommand_list(cli):
    unknown_list = "uhduh34852f56"
    unknown_list_result = cli.invoke(cade_task.cli.list, ["--list", unknown_list])
    assert unknown_list_result.exit_code is not 0
    assert "No reminders list matching {}".format(unknown_list) in unknown_list_result.output
