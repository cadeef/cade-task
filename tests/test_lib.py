"""Unit tests for lib.py"""

import json
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import MagicMock, patch

import pytest

from cade_task.lib import (
    _RENAME_RULES,
    ListNotFoundException,
    RunAndReturnResult,
    TaskCommandException,
    TaskException,
    TaskItem,
    TaskList,
    get_lists,
    list_name_from_path,
    reminders,
    run_and_return,
)

# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def make_calledprocesserror(
    returncode: int = 1,
    cmd: list[str] | None = None,
    stderr: str = "something went wrong",
    output: str = "",
) -> CalledProcessError:
    cmd = cmd or ["reminders", "show"]
    return CalledProcessError(
        returncode=returncode,
        cmd=cmd,
        output=output.encode(),
        stderr=stderr.encode(),
    )


def make_run_result(stdout: bytes, returncode: int = 0) -> MagicMock:
    result = MagicMock()
    result.stdout = stdout
    result.returncode = returncode
    result.args = ["reminders", "show-lists"]
    return result


def make_task_dict(**overrides) -> dict:
    base = {
        "title": "Buy milk",
        "list": "Groceries",
        "externalId": "abc-123",
        "isCompleted": False,
        "priority": 1,
        "index": 0,
        "notes": "2%",
        "dueDate": "2024-01-01",
        "startDate": "2023-12-31",
    }
    return {**base, **overrides}


# ---------------------------------------------------------------------------
# TaskItem
# ---------------------------------------------------------------------------


class TestTaskItem:
    def test_basic_construction(self):
        task = TaskItem(title="Buy milk", parent="Groceries")
        assert task.title == "Buy milk"
        assert task.parent == "Groceries"
        assert task.task_id is None
        assert task.is_complete is None

    def test_title_list_joined_on_init(self):
        task = TaskItem(title=["Buy", "some", "milk"], parent="Groceries")
        assert task.title == "Buy some milk"

    def test_title_string_unchanged(self):
        task = TaskItem(title="Already a string", parent="Work")
        assert task.title == "Already a string"

    def test_title_can_be_updated_after_init(self):
        task = TaskItem(title=["Initial", "title"], parent="Work")
        task.title = "Updated title"
        assert task.title == "Updated title"

    def test_optional_fields_default_to_none(self):
        task = TaskItem(title="Task", parent="List")
        for attr in ("task_id", "is_complete", "priority", "index", "notes", "due_date", "start_date"):
            assert getattr(task, attr) is None

    def test_from_dict_renames_keys(self):
        raw = make_task_dict()
        task = TaskItem.from_dict(raw)
        assert task.task_id == "abc-123"
        assert task.is_complete is False
        assert task.due_date == "2024-01-01"
        assert task.start_date == "2023-12-31"
        assert task.parent == "Groceries"

    def test_from_dict_passthrough_keys_unchanged(self):
        raw = {"title": "Read book", "parent": "Personal", "priority": 2}
        task = TaskItem.from_dict(raw)
        assert task.title == "Read book"
        assert task.priority == 2

    def test_from_dict_minimal(self):
        task = TaskItem.from_dict({"title": "Minimal", "list": "Inbox"})
        assert task.title == "Minimal"
        assert task.parent == "Inbox"

    def test_rename_rules_covers_all_camel_case_keys(self):
        camel_keys = {"externalId", "isCompleted", "dueDate", "startDate", "list"}
        assert camel_keys == set(_RENAME_RULES.keys())

    @patch("cade_task.lib.run_and_return")
    def test_add_calls_run_and_returns_task_item(self, mock_run):
        returned_dict = {"title": "Buy milk", "list": "Groceries", "externalId": "xyz"}
        mock_run.return_value = RunAndReturnResult(
            command="reminders add Groceries Buy milk",
            output=returned_dict,
            unmarshalled_output=b"",
            return_code=0,
        )
        task = TaskItem(title="Buy milk", parent="Groceries")
        result = task.add()
        mock_run.assert_called_once_with(["add", "Groceries", "Buy milk"], mode="json")
        assert isinstance(result, TaskItem)
        assert result.task_id == "xyz"

    @patch("cade_task.lib.run_and_return")
    def test_complete_calls_run_with_index(self, mock_run):
        mock_run.return_value = MagicMock()
        task = TaskItem(title="Task", parent="Work", index=3)
        task.complete()
        mock_run.assert_called_once_with(["complete", "Work", "3"])

    @patch("cade_task.lib.run_and_return")
    def test_edit_calls_run_with_correct_args(self, mock_run):
        mock_run.return_value = MagicMock()
        task = TaskItem(title="Updated title", parent="Work", index=2)
        task.edit()
        mock_run.assert_called_once_with(["edit", "Work", 2, "Updated title"])


# ---------------------------------------------------------------------------
# TaskList
# ---------------------------------------------------------------------------


class TestTaskList:
    def test_exists_true(self):
        with patch("cade_task.lib.get_lists", return_value=["Work", "Personal"]):
            assert TaskList(name="Work").exists() is True

    def test_exists_false(self):
        with patch("cade_task.lib.get_lists", return_value=["Work", "Personal"]):
            assert TaskList(name="Shopping").exists() is False

    @patch("cade_task.lib.run_and_return")
    def test_create_succeeds_when_list_absent(self, mock_run):
        mock_run.return_value = MagicMock()
        with patch("cade_task.lib.get_lists", return_value=[]):
            TaskList(name="NewList").create()
        mock_run.assert_called_once_with(["new-list", "NewList"], mode="raw")

    def test_create_raises_if_list_exists(self):
        with (
            patch("cade_task.lib.get_lists", return_value=["Existing"]),
            pytest.raises(TaskException, match="already exists"),
        ):
            TaskList(name="Existing").create()

    @patch("cade_task.lib.run_and_return")
    def test_tasks_returns_task_items(self, mock_run):
        raw_tasks = [
            {"title": "Task A", "list": "Work"},
            {"title": "Task B", "list": "Work"},
        ]
        mock_run.return_value = RunAndReturnResult(
            command="reminders show Work",
            output=raw_tasks,
            unmarshalled_output=b"",
            return_code=0,
        )
        tl = TaskList(name="Work")
        tasks = tl.tasks()
        assert len(tasks) == 2
        assert all(isinstance(t, TaskItem) for t in tasks)
        assert tasks[0].title == "Task A"

    @patch("cade_task.lib.run_and_return")
    def test_tasks_caches_result(self, mock_run):
        mock_run.return_value = RunAndReturnResult(
            command="reminders show Work",
            output=[{"title": "Task A", "list": "Work"}],
            unmarshalled_output=b"",
            return_code=0,
        )
        tl = TaskList(name="Work")
        tl.tasks()
        tl.tasks()  # second call should use cache
        mock_run.assert_called_once()

    @patch("cade_task.lib.run_and_return")
    def test_tasks_raises_list_not_found(self, mock_run):
        err = make_calledprocesserror(output="No reminders list matching 'Ghost'")
        mock_run.side_effect = TaskCommandException(err)
        with pytest.raises(ListNotFoundException, match="not found"):
            TaskList(name="Ghost").tasks()

    @patch("cade_task.lib.run_and_return")
    def test_tasks_reraises_other_command_exceptions(self, mock_run):
        err = make_calledprocesserror(stderr="permission denied", output="permission denied")
        mock_run.side_effect = TaskCommandException(err)
        with pytest.raises(TaskCommandException):
            TaskList(name="Work").tasks()


# ---------------------------------------------------------------------------
# list_name_from_path
# ---------------------------------------------------------------------------


class TestListNameFromPath:
    def test_returns_first_part_of_relative_path(self):
        assert list_name_from_path("/home/user/projects", "/home/user/projects/myapp/src") == "myapp"

    def test_returns_none_when_not_under_project_dir(self):
        assert list_name_from_path("/home/user/projects", "/tmp/other") is None

    def test_returns_none_when_same_as_project_dir(self):
        assert list_name_from_path("/home/user/projects", "/home/user/projects") is None

    def test_working_dir_defaults_to_cwd(self):
        parent = str(Path.cwd().parent)
        result = list_name_from_path(parent)
        assert result == Path.cwd().name

    def test_deeply_nested_path_returns_only_first_part(self):
        result = list_name_from_path("/base", "/base/project/a/b/c")
        assert result == "project"


# ---------------------------------------------------------------------------
# reminders()
# ---------------------------------------------------------------------------


class TestReminders:
    def test_returns_path_when_found(self):
        with patch("cade_task.lib.which", return_value="/usr/local/bin/reminders"):
            assert reminders() == "/usr/local/bin/reminders"

    def test_raises_when_not_found(self):
        with (
            patch("cade_task.lib.which", return_value=None),
            pytest.raises(TaskException, match="not found in PATH"),
        ):
            reminders()


# ---------------------------------------------------------------------------
# run_and_return
# ---------------------------------------------------------------------------


class TestRunAndReturn:
    @patch("cade_task.lib.run")
    def test_raw_mode_splits_lines(self, mock_run):
        mock_run.return_value = make_run_result(b"line1\nline2\nline3")
        with patch("cade_task.lib.reminders", return_value="/usr/bin/reminders"):
            result = run_and_return(["show-lists"], mode="raw")
        assert result.output == ["line1", "line2", "line3"]

    @patch("cade_task.lib.run")
    def test_json_mode_parses_output(self, mock_run):
        payload = [{"title": "Task", "list": "Work"}]
        mock_run.return_value = make_run_result(json.dumps(payload).encode())
        with patch("cade_task.lib.reminders", return_value="/usr/bin/reminders"):
            result = run_and_return(["show", "Work"], mode="json")
        assert result.output == payload

    @patch("cade_task.lib.run")
    def test_json_mode_appends_format_flag(self, mock_run):
        mock_run.return_value = make_run_result(b"[]")
        with patch("cade_task.lib.reminders", return_value="/usr/bin/reminders"):
            run_and_return(["show", "Work"], mode="json")
        called_cmd = mock_run.call_args[0][0]
        assert "--format" in called_cmd
        assert "json" in called_cmd

    @patch("cade_task.lib.run")
    def test_inject_reminder_prepends_reminders_binary(self, mock_run):
        mock_run.return_value = make_run_result(b"")
        with patch("cade_task.lib.reminders", return_value="/usr/bin/reminders"):
            run_and_return(["show-lists"], mode="raw", inject_reminder=True)
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd[0] == "/usr/bin/reminders"

    @patch("cade_task.lib.run")
    def test_no_inject_reminder_skips_binary(self, mock_run):
        mock_run.return_value = make_run_result(b"line")
        result = run_and_return(["echo", "hello"], mode="raw", inject_reminder=False)
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd[0] == "echo"
        assert result.output == ["line"]

    @patch("cade_task.lib.run")
    def test_int_args_cast_to_str(self, mock_run):
        mock_run.return_value = make_run_result(b"")
        with patch("cade_task.lib.reminders", return_value="/usr/bin/reminders"):
            run_and_return(["complete", "Work", 3], mode="raw")
        called_cmd = mock_run.call_args[0][0]
        assert "3" in called_cmd

    @patch("cade_task.lib.run")
    def test_invalid_mode_raises(self, mock_run):
        mock_run.return_value = make_run_result(b"data")
        with (
            patch("cade_task.lib.reminders", return_value="/usr/bin/reminders"),
            pytest.raises(TaskException, match="Invalid mode"),
        ):
            run_and_return(["show-lists"], mode="invalid")

    @patch("cade_task.lib.run")
    def test_called_process_error_raises_task_command_exception(self, mock_run):
        mock_run.side_effect = make_calledprocesserror()
        with (
            patch("cade_task.lib.reminders", return_value="/usr/bin/reminders"),
            pytest.raises(TaskCommandException),
        ):
            run_and_return(["show", "Work"])

    @patch("cade_task.lib.run")
    def test_result_fields_populated(self, mock_run):
        raw = b'["list1"]'
        mock_result = make_run_result(raw)
        mock_result.args = ["/usr/bin/reminders", "show-lists", "--format", "json"]
        mock_run.return_value = mock_result
        with patch("cade_task.lib.reminders", return_value="/usr/bin/reminders"):
            result = run_and_return(["show-lists"], mode="json")
        assert result.return_code == 0
        assert result.unmarshalled_output == raw
        assert "reminders" in result.command


# ---------------------------------------------------------------------------
# TaskCommandException
# ---------------------------------------------------------------------------


class TestTaskCommandException:
    def test_str_includes_cmd_and_stderr(self):
        err = make_calledprocesserror(returncode=2, cmd=["reminders", "show"], stderr="list not found")
        exc = TaskCommandException(err)
        assert "reminders show" in str(exc)
        assert "list not found" in str(exc)
        assert exc.returncode == 2

    def test_output_decoded_and_stripped(self):
        err = make_calledprocesserror(output="  some output  \n")
        exc = TaskCommandException(err)
        assert exc.output == "some output"

    def test_stdout_decoded_and_stripped(self):
        # CalledProcessError.stdout is an alias for output, so provide output here
        # instead of setting stdout separately in the helper.
        err = make_calledprocesserror(output="  stdout content  \n")
        exc = TaskCommandException(err)
        assert exc.stdout.strip() == "stdout content"


# ---------------------------------------------------------------------------
# get_lists
# ---------------------------------------------------------------------------


class TestGetLists:
    @patch("cade_task.lib.run_and_return")
    def test_returns_list_of_strings(self, mock_run):
        mock_run.return_value = RunAndReturnResult(
            command="reminders show-lists",
            output=["Work", "Personal", "Shopping"],
            unmarshalled_output=b"",
            return_code=0,
        )
        assert get_lists() == ["Work", "Personal", "Shopping"]

    @patch("cade_task.lib.run_and_return")
    def test_calls_show_lists_in_json_mode(self, mock_run):
        mock_run.return_value = RunAndReturnResult(
            command="reminders show-lists",
            output=[],
            unmarshalled_output=b"",
            return_code=0,
        )
        get_lists()
        mock_run.assert_called_once_with(["show-lists"], mode="json")
