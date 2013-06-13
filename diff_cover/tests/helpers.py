"""
Test helper functions.
"""
import random

HUNK_BUFFER = 2
MAX_LINE_LENGTH = 300
LINE_STRINGS = ['test',]


def line_numbers(start, end):
    """
    Return a list of line numbers, in [start, end] (inclusive).
    """
    return [line for line in range(start, end + 1)]


def git_diff_output(diff_dict, deleted_files=None, line_buffer=True):
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

    `line_buffer` controls whether extra lines are appended/prepended to the
    diff hunks.

    The content of the source files are randomly generated.

    Returns a byte string.
    """

    output = []

    # Entries for deleted files
    output.extend(_deleted_file_entries(deleted_files))

    # Entries for source files
    for (src_file, modified_lines) in diff_dict.items():

        output.extend(_source_file_entry(src_file, modified_lines, line_buffer))

    return '\n'.join(output)


def _deleted_file_entries(deleted_files):

    output = []

    if deleted_files is not None:

        for src_file in deleted_files:
            # File information
            output.append('diff --git a/{0} b/{1}'.format(src_file, src_file))
            output.append('index 629e8ad..91b8c0a 100644')
            output.append('--- a/{}'.format(src_file))
            output.append('+++ b/dev/null')

            # Choose a random number of lines
            num_lines = random.randint(1, 30)

            # Hunk information
            output.append('@@ -0,{} +0,0 @@'.format(num_lines))
            output.extend(['-' + _random_string() for _ in range(num_lines)])

    return output


def _source_file_entry(src_file, modified_lines, line_buffer):

    output = []

    # Line for the file names
    output.append('diff --git a/{0} b/{1}'.format(src_file, src_file))

    # Index line
    output.append('index 629e8ad..91b8c0a 100644')

    # Additions/deletions
    output.append('--- a/{}'.format(src_file))
    output.append('+++ b/{}'.format(src_file))

    # Hunk information
    for (start, end) in _hunks(modified_lines):
        output.extend(_hunk_entry(start, end, modified_lines, line_buffer))

    return output


def _hunk_entry(start, end, modified_lines, line_buffer):
    output = []

    # The actual hunk usually has a few lines before/after
    if line_buffer:
        start -= HUNK_BUFFER
        end += HUNK_BUFFER

        if start < 0:
            start = 0

    # Hunk definition line
    # Real `git diff` output would have different line numbers
    # for before/after the change, but since we're only interested
    # in after the change, we use the same numbers for both.
    length = end - start
    if length > 0:
        output.append('@@ -{0},{1} +{0},{1} @@'.format(start, length))

    # If we're only changing one line, then the `length` field gets
    # left off in the "after" file.  We still generate a random
    # placeholder for the length in the original file.
    else:
        original_length = random.randint(1, 100)
        output.append('@@ -{0},{1} +{0} @@'.format(start, 
                                                    original_length))

    # Output line modifications
    for line_number in range(start, end + 1):

        # This is a changed line, so prepend a + sign
        if line_number in modified_lines:

            # With some probability, introduce a deleted
            # line BEFORE the changed line
            if random.random() < 0.25:
                output.append('-' + _random_string())

            # Include the changed line
            output.append('+' + _random_string())

            # With some probability, introduce a deleted
            # line AFTER the changed line
            if random.random() < 0.25:
                output.append('-' + _random_string())

        # This is a line we didn't modify, so no + or - signs
        else:
            output.append(_random_string())

    return output


def _hunks(line_numbers):
    """
    Given a list of line numbers, return a list of hunks represented
    as `(start, end)` tuples.
    """

    # Identify contiguous lines as hunks
    hunks = []
    last_line = None

    for line in sorted(line_numbers):

        # If this is contiguous with the last line, continue the hunk
        # We're guaranteed at this point to have at least one hunk
        if (line - 1) == last_line:
            start, _ = hunks[-1]
            hunks[-1]= (start, line)

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
