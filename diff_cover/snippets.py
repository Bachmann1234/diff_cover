"""
Load snippets from source files to show violation lines
in HTML reports.
"""
from __future__ import unicode_literals
import pygments
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import guess_lexer_for_filename
from pygments.lexers.special import TextLexer
from pygments.util import ClassNotFound
import six

from diff_cover.git_path import GitPathTool
# If tokenize.open (Python>=3.2) is available, use that to open python files.
# Otherwise, use detect_encoding from lib2to3 (2.6, 2.7) wrapped the same way
# that tokenize.open would have.
try:
    from tokenize import open as openpy
except ImportError:
    def openpy(filename):
        from lib2to3.pgen2.tokenize import detect_encoding
        import io

        # The following is copied from tokenize.py in Python 3.2,
        # Copyright (c) 2001-2014 Python Software Foundation; All Rights Reserved
        buffer = io.open(filename, 'rb')
        encoding, lines = detect_encoding(buffer.readline)
        buffer.seek(0)
        text = io.TextIOWrapper(buffer, encoding, line_buffering=True)
        text.mode = 'r'
        return text


class Snippet(object):
    """
    A source code snippet.
    """

    VIOLATION_COLOR = '#ffcccc'
    DIV_CSS_CLASS = 'snippet'

    # Number of extra lines to include before and after
    # each snippet to provide context.
    NUM_CONTEXT_LINES = 4

    # Maximum distance between two violations within
    # a snippet.  If violations are further apart,
    # should split into two snippets.
    MAX_GAP_IN_SNIPPET = 4

    def __init__(self, src_tokens, src_filename,
                 start_line, violation_lines):
        """
        Create a source code snippet.

        `src_tokens` is a list of `(token_type, value)`
        tuples, parsed from the source file.
        NOTE: `value` must be `unicode`, not a `str`

        `src_filename` is the name of the source file,
        used to determine the source file language.

        `start_line` is the line number of first line
        in `src_str`.  The first line in the file is
        line number 1.

        `violation_lines` is a list of line numbers
        to highlight as violations.

        Raises a `ValueError` if `start_line` is less than 1
        """
        if start_line < 1:
            raise ValueError('Start line must be >= 1')

        self._src_tokens = src_tokens
        self._src_filename = src_filename
        self._start_line = start_line
        self._violation_lines = violation_lines

    @classmethod
    def style_defs(cls):
        """
        Return the CSS style definitions required
        by the formatted snippet.
        """
        formatter = HtmlFormatter()
        formatter.style.highlight_color = cls.VIOLATION_COLOR
        return formatter.get_style_defs()

    def html(self):
        """
        Return an HTML representation of the snippet.
        """
        formatter = HtmlFormatter(
            cssclass=self.DIV_CSS_CLASS,
            linenos=True,
            linenostart=self._start_line,
            hl_lines=self._shift_lines(
                self._violation_lines,
                self._start_line
            ),
            lineanchors=self._src_filename
        )

        return pygments.format(self.src_tokens(), formatter)

    def src_tokens(self):
        """
        Return a list of `(token_type, value)` tokens
        parsed from the source file.
        """
        return self._src_tokens

    def line_range(self):
        """
        Return a tuple of the form `(start_line, end_line)`
        indicating the start and end line number of the snippet.
        """
        num_lines = len(self.text().split('\n'))
        end_line = self._start_line + num_lines - 1
        return (self._start_line, end_line)

    def text(self):
        """
        Return the source text for the snippet.
        """
        return ''.join([val for _, val in self._src_tokens])

    @classmethod
    def load_snippets_html(cls, src_path, violation_lines):
        """
        Load snippets from the file at `src_path` and format
        them as HTML.

        See `load_snippets()` for details.
        """
        snippet_list = cls.load_snippets(src_path, violation_lines)
        return [snippet.html() for snippet in snippet_list]

    @classmethod
    def load_snippets(cls, src_path, violation_lines):
        """
        Load snippets from the file at `src_path` to show
        violations on lines in the list `violation_lines`
        (list of line numbers, starting at index 0).

        The file at `src_path` should be a text file (not binary).

        Returns a list of `Snippet` instances.

        Raises an `IOError` if the file could not be loaded.
        """
        # Load the contents of the file
        with openpy(GitPathTool.relative_path(src_path)) as src_file:
            contents = src_file.read()

        # Convert the source file to unicode (Python < 3)
        if isinstance(contents, six.binary_type):
            contents = contents.decode('utf-8', 'replace')

        # Construct a list of snippet ranges
        src_lines = contents.split('\n')
        snippet_ranges = cls._snippet_ranges(len(src_lines), violation_lines)

        # Parse the source into tokens
        token_stream = cls._parse_src(contents, src_path)

        # Group the tokens by snippet
        token_groups = cls._group_tokens(token_stream, snippet_ranges)

        return [
            Snippet(tokens, src_path, start, violation_lines)
            for (start, _), tokens in sorted(token_groups.items())
        ]

    @classmethod
    def _parse_src(cls, src_contents, src_filename):
        """
        Return a stream of `(token_type, value)` tuples
        parsed from `src_contents` (str)

        Uses `src_filename` to guess the type of file
        so it can highlight syntax correctly.
        """

        # Parse the source into tokens
        try:
            lexer = guess_lexer_for_filename(src_filename, src_contents)
        except ClassNotFound:
            lexer = TextLexer()

        # Ensure that we don't strip newlines from
        # the source file when lexing.
        lexer.stripnl = False

        return pygments.lex(src_contents, lexer)

    @classmethod
    def _group_tokens(cls, token_stream, range_list):
        """
        Group tokens into snippet ranges.

        `token_stream` is a generator that produces
        `(token_type, value)` tuples,

        `range_list` is a list of `(start, end)` tuples representing
        the (inclusive) range of line numbers for each snippet.

        Assumes that `range_list` is an ascending order by start value.

        Returns a dict mapping ranges to lists of tokens:
        {
            (4, 10): [(ttype_1, val_1), (ttype_2, val_2), ...],
            (29, 39): [(ttype_3, val_3), ...],
            ...
        }

        The algorithm is slightly complicated because a single token
        can contain multiple line breaks.
        """

        # Create a map from ranges (start/end tuples) to tokens
        token_map = {rng: [] for rng in range_list}

        # Keep track of the current line number; we will
        # increment this as we encounter newlines in token values
        line_num = 1

        for ttype, val in token_stream:

            # If there are newlines in this token,
            # we need to split it up and check whether
            # each line within the token is within one
            # of our ranges.
            if '\n' in val:
                val_lines = val.split('\n')

                # Check if the tokens match each range
                for (start, end), filtered_tokens in six.iteritems(token_map):

                    # Filter out lines that are not in this range
                    include_vals = [
                        val_lines[i] for i in
                        range(0, len(val_lines))
                        if i + line_num in range(start, end + 1)
                    ]

                    # If we found any lines, store the tokens
                    if len(include_vals) > 0:
                        token = (ttype, '\n'.join(include_vals))
                        filtered_tokens.append(token)

                # Increment the line number
                # by the number of lines we found
                line_num += len(val_lines) - 1

            # No newline in this token
            # If we're in the line range, add it
            else:
                # Check if the tokens match each range
                for (start, end), filtered_tokens in six.iteritems(token_map):

                    # If we got a match, store the token
                    if line_num in range(start, end + 1):
                        filtered_tokens.append((ttype, val))

                    # Otherwise, ignore the token

        return token_map

    @classmethod
    def _snippet_ranges(cls, num_src_lines, violation_lines):
        """
        Given the number of source file lines and list of
        violation line numbers, return a list of snippet
        ranges of the form `(start_line, end_line)`.

        Each snippet contains a few extra lines of context
        before/after the first/last violation.  Nearby
        violations are grouped within the same snippet.
        """
        current_range = (None, None)
        lines_since_last_violation = 0
        snippet_ranges = []
        for line_num in range(1, num_src_lines + 1):

            # If we have not yet started a snippet,
            # check if we can (is this line a violation?)
            if current_range[0] is None:
                if line_num in violation_lines:

                    # Expand to include extra context, but not before line 1
                    snippet_start = max(1, line_num - cls.NUM_CONTEXT_LINES)
                    current_range = (snippet_start, None)
                    lines_since_last_violation = 0

            # If we are within a snippet, check if we
            # can end the snippet (have we gone enough
            # lines without hitting a violation?)
            elif current_range[1] is None:
                if line_num in violation_lines:
                    lines_since_last_violation = 0

                elif lines_since_last_violation > cls.MAX_GAP_IN_SNIPPET:

                    # Expand to include extra context, but not after last line
                    snippet_end = line_num - lines_since_last_violation
                    snippet_end = min(
                        num_src_lines,
                        snippet_end + cls.NUM_CONTEXT_LINES
                    )
                    current_range = (current_range[0], snippet_end)

                    # Store the snippet and start looking for the next one
                    snippet_ranges.append(current_range)
                    current_range = (None, None)

            # Another line since the last violation
            lines_since_last_violation += 1

        # If we started a snippet but didn't finish it, do so now
        if current_range[0] is not None and current_range[1] is None:
            snippet_ranges.append((current_range[0], num_src_lines))

        return snippet_ranges

    @staticmethod
    def _shift_lines(line_num_list, start_line):
        """
        Shift all line numbers in `line_num_list` so that
        `start_line` is treated as line 1.

        For example, `[5, 8, 9]` with `start_line=3` would
        become `[3, 6, 7]`.

        Assumes that all entries in `line_num_list` are greater
        than or equal to `start_line`; otherwise, they will
        be excluded from the list.
        """
        return [line_num - start_line + 1
                for line_num in line_num_list
                if line_num >= start_line]
