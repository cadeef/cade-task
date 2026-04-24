"""Unit tests for the refactored cade_task.lib module."""

import json
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import MagicMock, patch

import pytest

from cade_task.lib import (
    ListNotFoundException,
    RunAndReturnResult,
    TaskCommandException,
    TaskException,
    TaskItem,
    TaskList,
    _RENAME_RULES,
    get_lists,
    list_name_from_path,
    reminders,
    run_and_return,
)


def make_calledprocesserror(
    returncode: int = 1,
    cmd: list[str] | None = None,
    stderr: str = "something went wrong",
    stdout: str = "",
    output: str = "",
) -> CalledProcessError:
    err = CalledProcessError(returncode, cmd or ["reminders", "show"])
    err.stderr = stderr.encode()
    err.stdout = stdout.encode()
    err.output = output.encode()
    return err


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

    def test_optional_fields_default_to_none(self):
        task = TaskItem(title="Task", parent="List")
        for attr in ("task_id", "is_complete", "priority", "index", "notes", "due_date", "start_date"):
            assert getattr(task, attr) is None

    def test_from_dict_renames_keys(self):
        task = TaskItem.from_dict(make_task_dict())
        assert task.task_id == "abc-123"
        assert task.is_complete is False
        assert task.due_date == "2024-01-01"
        assert task.start_date == "2023-12-31"
        assert task.parent == "Groceries"

    def test_from_dict_passthrough_keys_unchanged(self):
        task = TaskItem.from_dict({"title": "Read book", "parent": "Personal", "priority": 2})
        assert task.title == "Read book"
        assert task.priority == 2

    def test_rename_rules_covers_all_camel_case_keys(self):
        assert set(_RENAME_RULES) == {"externalId", "isCompleted", "dueDate", "startDate", "list"}

    @patch("cade_task.lib.run_and_return")
    def test_add_calls_run_and_returns_task_item(self, mock_run):
        mock_run.return_value = RunAndReturnResult(
            command="reminders add Groceries Buy milk",
            output={"title": "Buy milk", "list": "Groceries", "externalId": "xyz"},
            unmarshalled_output=b"",
            return_code=0,
        )
        result = TaskItem(title="Buy milk", parent="Groceries").add()
        mock_run.assert_called_once_with(["add", "Groceries", "Buy milk"], mode="json")
        assert isinstance(result, TaskItem)
        assert result.task_id == "xyz"

    @patch("cade_task.lib.run_and_return")
    def test_complete_calls_run_with_int_index(self, mock_run):
        TaskItem(title="Task", parent="Work", index=3).complete()
        mock_run.assert_called_once_with(["complete", "Work", 3])

    @patch("cade_task.lib.run_and_return")
    def test_edit_calls_run_with_correct_args(self, mock_run):
        task = TaskItem(title="Updated title", parent="Work", index=2)
        task.edit()
        mock_run.assert_called_once_with(["edit", "Work", 2, "Updated title"])

    @patch("cade_task.lib.run_and_return")
    def test_complete_raises_when_index_missing(self, mock_run):
        with pytest.raises(TaskException, match="does not have an index"):
            TaskItem(title="Task", parent="Work").complete()
        mock_run.assert_not_called()

    @patch("cade_task.lib.run_and_return")
    def test_edit_raises_when_index_missing(self, mock_run):
        with pytest.raises(TaskException, match="does not have an index"):
            TaskItem(title="Task", parent="Work").edit()
        mock_run.assert_not_called()


class TestTaskList:
    @patch("cade_task.lib.get_lists", return_value=["Work", "Personal"])
    def test_exists_true(self, _):
        assert TaskList(name="Work").exists() is True

    @patch("cade_task.lib.get_lists", return_value=["Work", "Personal"])
    def test_exists_false(self, _):
        assert TaskList(name="Shopping").exists() is False

    @patch("cade_task.lib.get_lists", return_value=[])
    @patch("cade_task.lib.run_and_return")
    def test_create_succeeds_when_list_absent_and_clears_cache(self, mock_run, _):
        task_list = TaskList(name="NewList")
        task_list._tasks = [TaskItem(title="Cached", parent="NewList")]
        task_list.create()
        mock_run.assert_called_once_with(["new-list", "NewList"], mode="raw")
        assert task_list._tasks is None

    @patch("cade_task.lib.get_lists", return_value=["Existing"])
    def test_create_raises_if_list_exists(self, _):
        with pytest.raises(TaskException, match="already exists"):
            TaskList(name="Existing").create()

    @patch("cade_task.lib.run_and_return")
    def test_tasks_returns_task_items(self, mock_run):
        mock_run.return_value = RunAndReturnResult(
            command="reminders show Work",
            output=[{"title": "Task A", "list": "Work"}, {"title": "Task B", "list": "Work"}],
            unmarshalled_output=b"",
            return_code=0,
        )
        tasks = TaskList(name="Work").tasks()
        assert [task.title for task in tasks] == ["Task A", "Task B"]
        assert all(isinstance(task, TaskItem) for task in tasks)

    @patch("cade_task.lib.run_and_return")
    def test_tasks_caches_result(self, mock_run):
        mock_run.return_value = RunAndReturnResult(
            command="reminders show Work",
            output=[{"title": "Task A", "list": "Work"}],
            unmarshalled_output=b"",
            return_code=0,
        )
        task_list = TaskList(name="Work")
        assert task_list.tasks() is task_list.tasks()
        mock_run.assert_called_once()

    @patch("cade_task.lib.run_and_return")
    def test_tasks_refresh_bypasses_cache(self, mock_run):
        mock_run.side_effect = [
            RunAndReturnResult("reminders show Work", [{"title": "Task A", "list": "Work"}], b"", 0),
            RunAndReturnResult("reminders show Work", [{"title": "Task B", "list": "Work"}], b"", 0),
        ]
        task_list = TaskList(name="Work")
        assert task_list.tasks()[0].title == "Task A"
        assert task_list.tasks(refresh=True)[0].title == "Task B"
        assert mock_run.call_count == 2

    @patch("cade_task.lib.run_and_return")
    def test_clear_cache_forces_next_fetch(self, mock_run):
        mock_run.side_effect = [
            RunAndReturnResult("reminders show Work", [{"title": "Task A", "list": "Work"}], b"", 0),
            RunAndReturnResult("reminders show Work", [{"title": "Task B", "list": "Work"}], b"", 0),
        ]
        task_list = TaskList(name="Work")
        assert task_list.tasks()[0].title == "Task A"
        task_list.clear_cache()
        assert task_list.tasks()[0].title == "Task B"

    @patch("cade_task.lib.run_and_return")
    def test_tasks_raises_list_not_found(self, mock_run):
        mock_run.side_effect = TaskCommandException(
            make_calledprocesserror(output="No reminders list matching 'Ghost'")
        )
        with pytest.raises(ListNotFoundException, match="not found"):
            TaskList(name="Ghost").tasks()

    @patch("cade_task.lib.run_and_return")
    def test_tasks_reraises_other_command_exceptions(self, mock_run):
        mock_run.side_effect = TaskCommandException(make_calledprocesserror(stderr="permission denied"))
        with pytest.raises(TaskCommandException):
            TaskList(name="Work").tasks()


class TestListNameFromPath:
    def test_returns_first_part_of_relative_path(self):
        assert list_name_from_path("/home/user/projects", "/home/user/projects/myapp/src") == "myapp"

    def test_returns_none_when_not_under_project_dir(self):
        assert list_name_from_path("/home/user/projects", "/tmp/other") is None

    def test_returns_none_when_same_as_project_dir(self):
        assert list_name_from_path("/home/user/projects", "/home/user/projects") is None

    def test_working_dir_defaults_to_cwd(self):
        assert list_name_from_path(Path.cwd().parent) == Path.cwd().name

    def test_deeply_nested_path_returns_only_first_part(self):
        assert list_name_from_path("/base", "/base/project/a/b/c") == "project"

    def test_accepts_path_objects(self):
        assert list_name_from_path(Path("/base"), Path("/base/project")) == "project"


class TestReminders:
    @patch("cade_task.lib.which", return_value="/usr/local/bin/reminders")
    def test_returns_path_when_found(self, _):
        assert reminders() == "/usr/local/bin/reminders"

    @patch("cade_task.lib.which", return_value=None)
    def test_raises_when_not_found(self, _):
        with pytest.raises(TaskException, match="not found in PATH"):
            reminders()


class TestRunAndReturn:
    @patch("cade_task.lib.reminders", return_value="/usr/bin/reminders")
    @patch("cade_task.lib.run")
    def test_raw_mode_splits_lines(self, mock_run, _):
        mock_run.return_value = make_run_result(b"line1\nline2\nline3")
        assert run_and_return(["show-lists"], mode="raw").output == ["line1", "line2", "line3"]

    @patch("cade_task.lib.reminders", return_value="/usr/bin/reminders")
    @patch("cade_task.lib.run")
    def test_json_mode_parses_output(self, mock_run, _):
        payload = [{"title": "Task", "list": "Work"}]
        mock_run.return_value = make_run_result(json.dumps(payload).encode())
        assert run_and_return(["show", "Work"], mode="json").output == payload

    @patch("cade_task.lib.reminders", return_value="/usr/bin/reminders")
    @patch("cade_task.lib.run")
    def test_json_mode_raises_clear_error_for_invalid_json(self, mock_run, _):
        mock_run.return_value = make_run_result(b"not-json")
        with pytest.raises(TaskException, match="returned invalid JSON"):
            run_and_return(["show", "Work"], mode="json")

    @patch("cade_task.lib.reminders", return_value="/usr/bin/reminders")
    @patch("cade_task.lib.run")
    def test_json_mode_appends_format_flag(self, mock_run, _):
        mock_run.return_value = make_run_result(b"[]")
        run_and_return(["show", "Work"], mode="json")
        assert mock_run.call_args[0][0][-2:] == ["--format", "json"]

    @patch("cade_task.lib.reminders", return_value="/usr/bin/reminders")
    @patch("cade_task.lib.run")
    def test_inject_reminder_prepends_reminders_binary(self, mock_run, _):
        mock_run.return_value = make_run_result(b"")
        run_and_return(["show-lists"], inject_reminder=True)
        assert mock_run.call_args[0][0][0] == "/usr/bin/reminders"

    @patch("cade_task.lib.run")
    def test_no_inject_reminder_skips_binary(self, mock_run):
        mock_run.return_value = make_run_result(b"line")
        result = run_and_return(["echo", "hello"], inject_reminder=False)
        assert mock_run.call_args[0][0][0] == "echo"
        assert result.output == ["line"]

    @patch("cade_task.lib.reminders", return_value="/usr/bin/reminders")
    @patch("cade_task.lib.run")
    def test_int_and_path_args_cast_to_str(self, mock_run, _):
        mock_run.return_value = make_run_result(b"")
        run_and_return(["complete", Path("/tmp/example"), 3])
        called_cmd = mock_run.call_args[0][0]
        assert "/tmp/example" in called_cmd
        assert "3" in called_cmd

    @patch("cade_task.lib.reminders", return_value="/usr/bin/reminders")
    @patch("cade_task.lib.run")
    def test_invalid_mode_raises(self, mock_run, _):
        mock_run.return_value = make_run_result(b"data")
        with pytest.raises(TaskException, match="Invalid mode"):
            run_and_return(["show-lists"], mode="invalid")  # type: ignore[arg-type]

    @patch("cade_task.lib.reminders", return_value="/usr/bin/reminders")
    @patch("cade_task.lib.run")
    def test_called_process_error_raises_task_command_exception(self, mock_run, _):
        mock_run.side_effect = make_calledprocesserror()
        with pytest.raises(TaskCommandException):
            run_and_return(["show", "Work"])

    @patch("cade_task.lib.reminders", return_value="/usr/bin/reminders")
    @patch("cade_task.lib.run")
    def test_result_fields_populated(self, mock_run, _):
        raw = b'["list1"]'
        mock_result = make_run_result(raw)
        mock_result.args = ["/usr/bin/reminders", "show-lists", "--format", "json"]
        mock_run.return_value = mock_result
        result = run_and_return(["show-lists"], mode="json")
        assert result.return_code == 0
        assert result.unmarshalled_output == raw
        assert "reminders" in result.command


class TestTaskCommandException:
    def test_str_includes_cmd_and_stderr(self):
        exc = TaskCommandException(
            make_calledprocesserror(returncode=2, cmd=["reminders", "show"], stderr="list not found")
        )
        assert "reminders show" in str(exc)
        assert "list not found" in str(exc)
        assert exc.returncode == 2

    def test_output_decoded_and_stripped(self):
        exc = TaskCommandException(make_calledprocesserror(output="  some output  \n"))
        assert exc.output == "  some output"

    def test_stdout_decoded_and_stripped(self):
        exc = TaskCommandException(make_calledprocesserror(stdout="  stdout content  \n"))
        assert exc.stdout == "  stdout content"

    def test_str_falls_back_to_stdout_when_stderr_empty(self):
        exc = TaskCommandException(make_calledprocesserror(stderr="", stdout="stdout details"))
        assert "stdout details" in str(exc)

    def test_handles_missing_process_streams(self):
        exc = TaskCommandException(CalledProcessError(1, ["reminders", "show"]))
        assert exc.output == ""
        assert exc.stdout == ""
        assert exc.stderr == ""
        assert "No output captured" in str(exc)


class TestGetLists:
    @patch("cade_task.lib.run_and_return")
    def test_returns_list_of_strings(self, mock_run):
        mock_run.return_value = RunAndReturnResult("reminders show-lists", ["Work", "Personal"], b"", 0)
        assert get_lists() == ["Work", "Personal"]

    @patch("cade_task.lib.run_and_return")
    def test_calls_show_lists_in_json_mode(self, mock_run):
        mock_run.return_value = RunAndReturnResult("reminders show-lists", [], b"", 0)
        get_lists()
        mock_run.assert_called_once_with(["show-lists"], mode="json")
