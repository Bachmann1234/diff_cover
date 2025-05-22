# pylint: disable=missing-function-docstring

"""Test for diff_cover.git_diff"""

import pytest

from diff_cover.command_runner import CommandError
from diff_cover.git_diff import GitDiffTool


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


@pytest.fixture
def tool():
    return GitDiffTool(range_notation="...", ignore_whitespace=False)


@pytest.fixture
def set_git_diff_output(process):
    def _inner(stdout, stderr, returncode=0):
        process.communicate.return_value = (stdout, stderr)
        process.returncode = returncode

    return _inner


@pytest.fixture
def check_diff_committed(subprocess, set_git_diff_output):
    def _inner(diff_range_notation, ignore_whitespace):
        tool_ = GitDiffTool(
            range_notation=diff_range_notation, ignore_whitespace=ignore_whitespace
        )

        set_git_diff_output("test output", "")
        output = tool_.diff_committed()

        # Expect that we get the correct output
        assert output == "test output"

        # Expect that the correct command was executed
        expected = [
            "git",
            "-c",
            "diff.mnemonicprefix=no",
            "-c",
            "diff.noprefix=no",
            "diff",
            "--no-color",
            "--no-ext-diff",
            "-U0",
        ]
        if ignore_whitespace:
            expected.append("--ignore-all-space")
            expected.append("--ignore-blank-lines")
        expected.append(f"origin/main{diff_range_notation}HEAD")
        subprocess.Popen.assert_called_with(
            expected, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

    return _inner


def test_diff_committed(check_diff_committed):
    check_diff_committed("...", ignore_whitespace=False)
    check_diff_committed("...", ignore_whitespace=True)
    check_diff_committed("..", ignore_whitespace=False)
    check_diff_committed("..", ignore_whitespace=True)


def test_diff_unstaged(set_git_diff_output, tool, subprocess):
    set_git_diff_output("test output", "")
    output = tool.diff_unstaged()

    # Expect that we get the correct output
    assert output == "test output"

    # Expect that the correct command was executed
    expected = [
        "git",
        "-c",
        "diff.mnemonicprefix=no",
        "-c",
        "diff.noprefix=no",
        "diff",
        "--no-color",
        "--no-ext-diff",
        "-U0",
    ]
    subprocess.Popen.assert_called_with(
        expected, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def test_diff_staged(tool, subprocess, set_git_diff_output):
    set_git_diff_output("test output", "")
    output = tool.diff_staged()

    # Expect that we get the correct output
    assert output == "test output"

    # Expect that the correct command was executed
    expected = [
        "git",
        "-c",
        "diff.mnemonicprefix=no",
        "-c",
        "diff.noprefix=no",
        "diff",
        "--no-color",
        "--no-ext-diff",
        "-U0",
        "--cached",
    ]
    subprocess.Popen.assert_called_with(
        expected, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def test_diff_missing_branch_error(set_git_diff_output, tool, subprocess):
    # Override the default compare branch
    set_git_diff_output("test output", "fatal error", 1)
    with pytest.raises(CommandError):
        tool.diff_committed(compare_branch="release")

    set_git_diff_output(
        "test output",
        "ambiguous argument 'origin/main...HEAD': "
        "unknown revision or path not in the working tree.",
        1,
    )
    with pytest.raises(ValueError):
        tool.diff_committed(compare_branch="release")


def test_diff_committed_compare_branch(set_git_diff_output, tool, subprocess):
    # Override the default compare branch
    set_git_diff_output("test output", "")
    output = tool.diff_committed(compare_branch="release")

    # Expect that we get the correct output
    assert output == "test output"

    # Expect that the correct command was executed
    expected = [
        "git",
        "-c",
        "diff.mnemonicprefix=no",
        "-c",
        "diff.noprefix=no",
        "diff",
        "--no-color",
        "--no-ext-diff",
        "-U0",
        "release...HEAD",
    ]
    subprocess.Popen.assert_called_with(
        expected, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def test_errors(set_git_diff_output, tool):
    set_git_diff_output("test output", "fatal error", 1)

    with pytest.raises(CommandError):
        tool.diff_unstaged()

    with pytest.raises(CommandError):
        tool.diff_staged()

    with pytest.raises(CommandError):
        tool.diff_unstaged()


@pytest.mark.parametrize(
    "output,expected",
    [
        ("", []),
        ("\n", []),
        ("a.py\n", ["a.py"]),
        ("a.py\nb.py\n", ["a.py", "b.py"]),
    ],
)
def test_untracked(tool, set_git_diff_output, output, expected):
    set_git_diff_output(output, b"")
    assert tool.untracked() == expected


def test_git_diff_tool_untracked_cache(tool, set_git_diff_output):
    set_git_diff_output("file.txt\nfile2.txt\n", "")
    output = tool.untracked()
    assert output == ["file.txt", "file2.txt"]

    set_git_diff_output("file2.txt\n", "")
    output = tool.untracked()
    assert output == ["file.txt", "file2.txt"]
