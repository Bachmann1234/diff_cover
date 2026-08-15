# pylint: disable=missing-function-docstring

"""Tests for the message shown when a required executable is not on PATH.

See https://github.com/Bachmann1234/diff_cover/issues/303
"""

import pytest

from diff_cover.command_runner import (
    GIT_INSTALL_URL,
    CommandError,
    ExecutableNotFoundError,
    execute,
)


@pytest.fixture
def missing_git(mocker):
    """Make every subprocess launch fail the way a missing `git` does."""
    return mocker.patch(
        "diff_cover.command_runner.subprocess.Popen",
        side_effect=FileNotFoundError(2, "No such file or directory", "git"),
    )


@pytest.fixture
def failing_git(mocker):
    """Make `git` run and fail, which is a different thing entirely."""
    process = mocker.Mock()
    process.returncode = 1
    process.communicate.return_value = (b"", b"fatal: not a git repository")
    popen = mocker.patch("diff_cover.command_runner.subprocess.Popen")
    popen.return_value.__enter__.return_value = process
    popen.return_value.__exit__.return_value = None
    return popen


def test_execute_turns_a_missing_executable_into_a_helpful_error(missing_git):
    with pytest.raises(ExecutableNotFoundError) as exc_info:
        execute(["git", "rev-parse", "--show-toplevel"])

    message = str(exc_info.value)
    assert "git" in message
    assert "PATH" in message
    assert message.endswith(f"See {GIT_INSTALL_URL} for installation instructions.")


def test_the_new_error_stays_a_command_error(missing_git):
    """Callers that already catch CommandError must keep working."""
    assert issubclass(ExecutableNotFoundError, CommandError)
    with pytest.raises(CommandError):
        execute(["git", "rev-parse", "--show-toplevel"])


def test_execute_does_not_link_git_docs_for_other_executables(mocker):
    mocker.patch(
        "diff_cover.command_runner.subprocess.Popen",
        side_effect=FileNotFoundError(2, "No such file or directory", "pycodestyle"),
    )

    with pytest.raises(ExecutableNotFoundError) as exc_info:
        execute(["pycodestyle", "--version"])

    message = str(exc_info.value)
    assert "pycodestyle" in message
    assert GIT_INSTALL_URL not in message


def test_diff_cover_main_reports_missing_git_without_a_traceback(missing_git, caplog):
    from diff_cover.diff_cover_tool import main

    assert main(["diff-cover", "coverage.xml"]) == 1
    assert "PATH" in caplog.text


def test_diff_quality_main_reports_missing_git_without_a_traceback(missing_git, caplog):
    from diff_cover.diff_quality_tool import main

    assert main(["diff-quality", "--violations", "pycodestyle"]) == 1
    assert "PATH" in caplog.text


def test_a_command_that_runs_and_fails_is_left_alone(failing_git):
    """Control. Green before and after: only a *missing* binary is reworded."""
    with pytest.raises(CommandError) as exc_info:
        execute(["git", "status"])

    assert not isinstance(exc_info.value, ExecutableNotFoundError)
    message = str(exc_info.value)
    assert "fatal: not a git repository" in message
    assert "PATH" not in message
