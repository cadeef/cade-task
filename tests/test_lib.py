import pytest

from cade_task.lib import list_name_from_path


@pytest.mark.parametrize(
    "working_dir,project_dir,expected",
    (
        ("/home/bill", "/home/bill/work", None),
        ("/home/bill/work", "/home/bill/work", None),
        ("/etc/", "/home/bill/work/", None),
        ("/home/bill/work/my_project", "/home/bill/work", "my_project"),
        ("/home/bill/work/my_project/nested_dir", "/home/bill/work", "my_project"),
        (
            "/home/bill/work/my_project/nested_dir/second/nested_dir",
            "/home/bill/work",
            "my_project",
        ),
    ),
)
def test_list_name_from_path(working_dir, project_dir, expected):
    assert list_name_from_path(project_dir, working_dir) == expected


def test_get_lists():
    pass


def test_run_and_return():
    pass


def test_taskitem():
    pass


def test_taskitem__add():
    pass


def test_taskitem__complete():
    pass


def test_taskitem__edit():
    pass
