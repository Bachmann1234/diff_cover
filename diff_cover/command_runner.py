import six
import subprocess

import sys


class CommandError(Exception):
    """
    Error raised when a command being excuted returns an error
    """
    pass


def execute(command):
    """Execute provided command returning the stdout
    Args:
        command (list[str]): list of tokens to execute as your command.
        subprocess_mod (module): Defaults to pythons subprocess module but you can optionally pass in
        another. This is mostly for testing purposes
    Returns:
        str - Stdout of the command passed in. This will be Unicode for python < 3. Str for python 3
    Raises:
        ValueError if there is a error running the command
    """
    stdout_pipe = subprocess.PIPE
    process = subprocess.Popen(
        command, stdout=stdout_pipe,
        stderr=stdout_pipe
    )
    try:
        stdout, stderr = process.communicate()
    except OSError:
        sys.stderr.write(" ".join(
                [cmd.decode(sys.getfilesystemencoding())
                 if isinstance(cmd, bytes) else cmd
                 for cmd in command])
        )
        raise

    stderr = _ensure_unicode(stderr)
    # If we get a non-empty output to stderr, raise an exception
    if bool(stderr) and process.returncode:
        raise CommandError(stderr)

    return _ensure_unicode(stdout), stderr


def run_command_for_code(command):
    """
    Returns command's exit code.
    """
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    process.communicate()
    exit_code = process.returncode
    return exit_code


def _ensure_unicode(text):
    """
    Ensures the text passed in becomes unicode
    Args:
        text (str|unicode)
    Returns:
        unicode
    """
    if isinstance(text, six.binary_type):
        return text.decode(sys.getfilesystemencoding(), 'replace')
    else:
        return text
