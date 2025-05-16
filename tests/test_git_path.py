# pylint: disable=missing-function-docstring

"""Test for diff_cover.git_path"""

import pytest

from diff_cover.git_path import GitPathTool


@pytest.fixture(autouse=True)
def patch_git_path_tool(mocker):
    mocker.patch.object(GitPathTool, "_root", None)
    mocker.patch.object(GitPathTool, "_cwd", None)


@pytest.fixture
def process(mocker):
    process_ = mocker.Mock()
    process_.returncode = 0
    return process_


@pytest.fixture(autouse=True)
def subprocess(mocker, process):
    subprocess_ = mocker.patch("diff_cover.command_runner.subprocess")
    subprocess_.Popen.return_value = process
    return subprocess_


def test_project_root_command(process, subprocess):
    process.communicate.return_value = (b"/phony/path", b"")

    GitPathTool.set_cwd(b"/phony/path")

    # Expect that the correct command was executed
    expected = ["git", "rev-parse", "--show-toplevel", "--encoding=utf-8"]
    subprocess.Popen.assert_called_with(
        expected, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def test_relative_path(process):
    process.communicate.return_value = (b"/home/user/work/diff-cover", b"")

    expected = "violations_reporter.py"
    cwd = "/home/user/work/diff-cover/diff_cover"

    GitPathTool.set_cwd(cwd)
    path = GitPathTool.relative_path("diff_cover/violations_reporter.py")

    # Expect relative path from diff_cover
    assert path == expected


def test_absolute_path(process):
    process.communicate.return_value = (
        b"/home/user/work dir/diff-cover\n--encoding=utf-8\n",
        b"",
    )

    expected = "/home/user/work dir/diff-cover/other_package/file.py"
    cwd = "/home/user/work dir/diff-cover/diff_cover"

    GitPathTool.set_cwd(cwd)
    path = GitPathTool.absolute_path("other_package/file.py")

    # Expect absolute path to file.py
    assert path == expected


def test_set_cwd_unicode(process):
    process.communicate.return_value = (b"\xe2\x94\xbb\xe2\x94\x81\xe2\x94\xbb", b"")

    expected = "\u253b\u2501\u253b/other_package/file.py"
    cwd = "\\u253b\\u2501\\u253b/diff_cover\n--encoding=utf-8\n"

    GitPathTool.set_cwd(cwd)
    path = GitPathTool.absolute_path("other_package/file.py")

    # Expect absolute path to file.py
    assert path == expected


def test_set_cwd_unicode_byte_passed_in_for_cwd(process):
    process.communicate.return_value = (
        b"\xe2\x94\xbb\xe2\x94\x81\xe2\x94\xbb\n--encoding=utf-8\n",
        b"",
    )

    expected = "\u253b\u2501\u253b/other_package/file.py"
    cwd = b"\\u253b\\u2501\\u253b/diff_cover"

    GitPathTool.set_cwd(cwd)
    path = GitPathTool.absolute_path("other_package/file.py")

    # Expect absolute path to file.py
    assert path == expected
