# pylint: disable=missing-function-docstring

"""Test for diff_cover.git_diff.GitDiffFileTool"""

import pytest

from diff_cover.git_diff import GitDiffFileTool


@pytest.fixture
def mock_file(mocker):
    def _inner(file_content):
        mock_open = mocker.mock_open(read_data=file_content)
        mocker.patch("builtins.open", mock_open)

    return _inner


@pytest.fixture
def diff_tool():
    def _inner(file):
        return GitDiffFileTool(file)

    return _inner


def test_diff_file_not_found(mocker, diff_tool):
    mocker.patch("builtins.open", side_effect=IOError)

    _diff_tool = diff_tool("non_existent_diff_file.txt")

    with pytest.raises(ValueError) as excinfo:
        _diff_tool.diff_committed()

    assert (
        f"Could not read the diff file. Make sure '{_diff_tool.diff_file_path}' exists?"
        in str(excinfo.value)
    )
    assert _diff_tool.diff_file_path == "non_existent_diff_file.txt"


def test_large_diff_file(mock_file, diff_tool):
    large_diff = "diff --git a/file1 b/file2\n" * 1000000

    mock_file(large_diff)

    _diff_tool = diff_tool("large_diff_file.txt")

    assert _diff_tool.diff_committed() == large_diff
    assert _diff_tool.diff_file_path == "large_diff_file.txt"


def test_diff_committed(mock_file, diff_tool):
    diff = "diff --git a/file1 b/file2\n"

    mock_file(diff)

    _diff_tool = diff_tool("diff_file.txt")

    assert _diff_tool.diff_committed() == diff
    assert _diff_tool.diff_file_path == "diff_file.txt"


def test_empty_diff_file(mock_file, diff_tool):
    empty_diff = ""

    mock_file(empty_diff)

    _diff_tool = diff_tool("empty_diff.txt")

    assert _diff_tool.diff_committed() == empty_diff
    assert _diff_tool.diff_file_path == "empty_diff.txt"
