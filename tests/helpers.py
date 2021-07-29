"""
Test helper functions.
"""
import os.path
import random

HUNK_BUFFER = 2
MAX_LINE_LENGTH = 300
LINE_STRINGS = ["test", "+ has a plus sign", "- has a minus sign"]


def fixture_path(rel_path):
    """
    Returns the absolute path to a fixture file
    given `rel_path` relative to the fixture directory.
    """
    fixture_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    return os.path.join(fixture_dir, rel_path)


def load_fixture(rel_path, encoding=None):
    """
    Return the contents of the file at `rel_path`
    (relative path to the "fixtures" directory).

    If `encoding` is not None, attempts to decode
    the contents as `encoding` (e.g. 'utf-8').
    """
    with open(fixture_path(rel_path), encoding=encoding or "utf-8") as fixture_file:
        contents = fixture_file.read()

    if encoding is not None and isinstance(contents, bytes):
        contents = contents.decode(encoding)

    return contents


def line_numbers(start, end):
    """
    Return a list of line numbers, in [start, end] (inclusive).
    """
    return list(range(start, end + 1))


def git_diff_output(diff_dict, deleted_files=None):
    """
    Construct fake output from `git diff` using the description
    defined by `diff_dict`, which is a dictionary of the form:

        {
            SRC_FILE_NAME: MODIFIED_LINES,
            ...
        }

    where `SRC_FILE_NAME` is the name of a source file in the diff,
    and `MODIFIED_LINES` is a list of lines added or changed in the
    source file.

    `deleted_files` is a list of files that have been deleted

    The content of the source files are randomly generated.

    Returns a byte string.
    """

    output = []

    # Entries for deleted files
    output.extend(_deleted_file_entries(deleted_files))

    # Entries for source files
    for (src_file, modified_lines) in diff_dict.items():

        output.extend(_source_file_entry(src_file, modified_lines))

    return "\n".join(output)


def _deleted_file_entries(deleted_files):
    """
    Create fake `git diff` output for files that have been
    deleted in this changeset.

    `deleted_files` is a list of files deleted in the changeset.

    Returns a list of lines in the diff output.
    """

    output = []

    if deleted_files is not None:

        for src_file in deleted_files:
            # File information
            output.append(f"diff --git a/{src_file} b/{src_file}")
            output.append("index 629e8ad..91b8c0a 100644")
            output.append(f"--- a/{src_file}")
            output.append("+++ b/dev/null")

            # Choose a random number of lines
            num_lines = random.randint(1, 30)

            # Hunk information
            output.append(f"@@ -0,{num_lines} +0,0 @@")
            output.extend(["-" + _random_string() for _ in range(num_lines)])

    return output


def _source_file_entry(src_file, modified_lines):
    """
    Create fake `git diff` output for added/modified lines.

    `src_file` is the source file with the changes;
    `modified_lines` is the list of modified line numbers.

    Returns a list of lines in the diff output.
    """

    output = []

    # Line for the file names
    output.append(f"diff --git a/{src_file} b/{src_file}")

    # Index line
    output.append("index 629e8ad..91b8c0a 100644")

    # Additions/deletions
    output.append(f"--- a/{src_file}")
    output.append(f"+++ b/{src_file}")

    # Hunk information
    for (start, end) in _hunks(modified_lines):
        output.extend(_hunk_entry(start, end, modified_lines))

    return output


def _hunk_entry(start, end, modified_lines):
    """
    Generates fake `git diff` output for a hunk,
    where `start` and `end` are the start/end lines of the hunk
    and `modified_lines` is a list of modified lines in the hunk.

    Just as `git diff` does, this will include a few lines before/after
    the changed lines in each hunk.
    """
    output = []

    # The actual hunk usually has a few lines before/after
    start -= HUNK_BUFFER
    end += HUNK_BUFFER

    start = max(start, 0)

    # Hunk definition line
    # Real `git diff` output would have different line numbers
    # for before/after the change, but since we're only interested
    # in after the change, we use the same numbers for both.
    length = end - start
    output.append("@@ -{0},{1} +{0},{1} @@".format(start, length))

    # Output line modifications
    for line_number in range(start, end + 1):

        # This is a changed line, so prepend a + sign
        if line_number in modified_lines:

            # Delete the old line
            output.append("-" + _random_string())

            # Include the changed line
            output.append("+" + _random_string())

        # This is a line we didn't modify, so no + or - signs
        # but prepend with a space.
        else:
            output.append(" " + _random_string())

    return output


def _hunks(modified_lines):
    """
    Given a list of line numbers, return a list of hunks represented
    as `(start, end)` tuples.
    """

    # Identify contiguous lines as hunks
    hunks = []
    last_line = None

    for line in sorted(modified_lines):

        # If this is contiguous with the last line, continue the hunk
        # We're guaranteed at this point to have at least one hunk
        if (line - 1) == last_line:
            start, _ = hunks[-1]
            hunks[-1] = (start, line)

        # If non-contiguous, start a new hunk with just the current line
        else:
            hunks.append((line, line))

        # Store the last line
        last_line = line

    return hunks


def _random_string():
    """
    Return a random byte string with length in the range
    [0, `MAX_LINE_LENGTH`] (inclusive).
    """
    return random.choice(LINE_STRINGS)
