import subprocess
import sys

GIT_INSTALL_URL = "https://git-scm.com/book/en/v2/Getting-Started-Installing-Git"


class CommandError(Exception):
    """
    Error raised when a command being executed returns an error
    """


class ExecutableNotFoundError(CommandError):
    """
    Error raised when the executable of a command cannot be found at all.

    This is a `CommandError` so that existing handling keeps working, but a
    distinct type so the command line tools can tell "your tooling is not
    installed" apart from "the command ran and failed".
    """


def execute(command, exit_codes=None):
    """Execute provided command returning the stdout
    Args:
        command (list[str]): list of tokens to execute as your command.
        exit_codes (list[int]): exit codes which do not indicate error.
        subprocess_mod (module): Defaults to pythons subprocess module but you can optionally pass
        in another. This is mostly for testing purposes
    Returns:
        str - Stdout of the command passed in. This will be Unicode for python < 3. Str for python 3
    Raises:
        ValueError if there is a error running the command
    """
    if exit_codes is None:
        exit_codes = [0]

    stdout_pipe = subprocess.PIPE
    try:
        popen = subprocess.Popen(command, stdout=stdout_pipe, stderr=stdout_pipe)
    except FileNotFoundError as exc:
        raise ExecutableNotFoundError(_executable_not_found_message(command)) from exc

    with popen as process:
        try:
            stdout, stderr = process.communicate()
        except OSError:
            sys.stderr.write(" ".join(_ensure_unicode(cmd) for cmd in command))
            raise

    stderr = _ensure_unicode(stderr)
    if process.returncode not in exit_codes:
        raise CommandError(stderr)

    return _ensure_unicode(stdout), stderr


def run_command_for_code(command):
    """
    Returns command's exit code.
    """
    try:
        with subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        ) as process:
            process.communicate()
    except FileNotFoundError:
        return 1
    return process.returncode


def _executable_not_found_message(command):
    """
    Explain that the executable of `command` is not installed or not on PATH.
    """
    executable = _ensure_unicode(command[0]) if command else ""
    message = (
        f"'{executable}' was not found. diff-cover needs '{executable}' to be "
        "installed and on your PATH in order to run."
    )
    if executable == "git":
        message += f" See {GIT_INSTALL_URL} for installation instructions."
    return message


def _ensure_unicode(text):
    """
    Ensures the text passed in becomes unicode
    Args:
        text (str|unicode)
    Returns:
        unicode
    """
    if isinstance(text, bytes):
        return text.decode(sys.getfilesystemencoding(), "replace")
    return text
