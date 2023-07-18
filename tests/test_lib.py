import pytest

from cade_task.lib import list_resolve


@pytest.mark.parametrize(
    "working_dir,project_dir,expected",
    (
        ("/home/bill", "/home/bill/work", None),
        ("/home/bill/work", "/home/bill/work", None),
        ("/etc/", "/home/bill/work/", None),
        ("/home/bill/work/my_project", "/home/bill/work", "my_project"),
        ("/home/bill/work/my_project/is/somewhere", "/home/bill/work", "my_project"),
    ),
)
def test_list_resolve(working_dir, project_dir, expected):
    assert list_resolve(project_dir, working_dir) == expected


def test_get_lists():
    pass


def test_get_tasks():
    pass


def test_run_and_return():
    pass
