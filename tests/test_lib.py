import pytest
from devtools import debug  # noqa: F401

from cade_task.lib import TaskItem, list_name_from_path


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


def test_taskitem__from_dict():
    test_dict = {
        "externalId": "CC7A70EB-0526-47AC-A4E3-D0EA5B2CF491",
        "isCompleted": False,
        "list": "test",
        "priority": 0,
        "title": "this is a magic test",
    }
    task = TaskItem.from_dict(test_dict)
    assert task == TaskItem(
        **{
            "id": "CC7A70EB-0526-47AC-A4E3-D0EA5B2CF491",
            "is_complete": False,
            "parent": "test",
            "priority": 0,
            "title": "this is a magic test",
        }
    )


def test_taskitem__add():
    pass


def test_taskitem__complete():
    pass


def test_taskitem__edit():
    pass


def test_tasklist__tasks():
    pass


def test_tasklist__exists():
    pass


def test_tasklist__create():
    pass
