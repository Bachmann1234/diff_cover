from __future__ import unicode_literals

import io
import mock
import os
import tempfile
from pygments.token import Token
from diff_cover.snippets import Snippet
from diff_cover.tests.helpers import load_fixture,\
    fixture_path, assert_long_str_equal
import six
import unittest


class SnippetTest(unittest.TestCase):

    SRC_TOKENS = [
        (Token.Comment, '# Test source'),
        (Token.Text, '\n'),
        (Token.Keyword, 'def'),
        (Token.Text, ' '),
        (Token.Name.Function, 'test_func'),
        (Token.Punctuation, '('),
        (Token.Name, 'arg'),
        (Token.Punctuation, ')'),
        (Token.Punctuation, ':'),
        (Token.Text, '\n'),
        (Token.Text, '    '),
        (Token.Keyword, 'print'),
        (Token.Text, ' '),
        (Token.Name, 'arg'),
        (Token.Text, '\n'),
        (Token.Text, '    '),
        (Token.Keyword, 'return'),
        (Token.Text, ' '),
        (Token.Name, 'arg'),
        (Token.Text, ' '),
        (Token.Operator, '+'),
        (Token.Text, ' '),
        (Token.Literal.Number.Integer, '5'),
        (Token.Text, '\n'),
    ]

    FIXTURES = {
        'style': 'snippet.css',
        'default': 'snippet_default.html',
        'invalid_violations': 'snippet_invalid_violations.html',
        'no_filename_ext': 'snippet_no_filename_ext.html',
        'unicode': 'snippet_unicode.html',
    }

    def test_style_defs(self):
        style_str = Snippet.style_defs()
        expected_styles = load_fixture(self.FIXTURES['style']).strip()

        # Check that a sample of the styles are present
        # (use only a sample to make the test more robust
        # against Pygment changes).
        for expect_line in expected_styles.split('\n'):
            self.assertIn(expect_line, style_str)

    def test_format(self):
        self._assert_format(
            self.SRC_TOKENS, 'test.py',
            4, [4, 6], self.FIXTURES['default']
        )

    def test_format_with_invalid_start_line(self):
        for start_line in [-2, -1, 0]:
            with self.assertRaises(ValueError):
                Snippet('# test', 'test.py', start_line, [])

    def test_format_with_invalid_violation_lines(self):

        # Violation lines outside the range of lines in the file
        # should be ignored.
        self._assert_format(
            self.SRC_TOKENS, 'test.py',
            1, [-1, 0, 5, 6],
            self.FIXTURES['invalid_violations']
        )

    def test_no_filename_ext(self):

        # No filename extension: should default to text lexer
        self._assert_format(
            self.SRC_TOKENS, 'test',
            4, [4, 6],
            self.FIXTURES['no_filename_ext']
        )

    def test_unicode(self):

        unicode_src = [(Token.Text, 'var = \u0123 \u5872 \u3389')]

        self._assert_format(
            unicode_src, 'test.py',
            1, [], self.FIXTURES['unicode']
        )

    def _assert_format(self, src_tokens, src_filename,
                       start_line, violation_lines,
                       expected_fixture):

        snippet = Snippet(src_tokens, src_filename,
                          start_line, violation_lines)
        result = snippet.html()

        expected_str = load_fixture(expected_fixture, encoding='utf-8')

        assert_long_str_equal(expected_str, result, strip=True)
        self.assertTrue(isinstance(result, six.text_type))


class SnippetLoaderTest(unittest.TestCase):

    def setUp(self):
        """
        Create a temporary source file.
        """
        _, self._src_path = tempfile.mkstemp()

        # Path tool should not be aware of testing command
        path_mock = mock.patch('diff_cover.violationsreporters.violations_reporter.GitPathTool').start()
        path_mock.absolute_path = lambda path: path
        path_mock.relative_path = lambda path: path

    def tearDown(self):
        """
        Delete the temporary source file.
        """
        os.remove(self._src_path)
        mock.patch.stopall()

    def test_one_snippet(self):
        self._init_src_file(10)
        violations = [2, 3, 4, 5]
        expected_ranges = [(1, 9)]
        self._assert_line_range(violations, expected_ranges)

    def test_multiple_snippets(self):
        self._init_src_file(100)
        violations = [30, 31, 32, 35, 36, 60, 62]
        expected_ranges = [(26, 40), (56, 66)]
        self._assert_line_range(violations, expected_ranges)

    def test_no_lead_line(self):
        self._init_src_file(10)
        violations = [1, 2, 3]
        expected_ranges = [(1, 7)]
        self._assert_line_range(violations, expected_ranges)

    def test_no_lag_line(self):
        self._init_src_file(10)
        violations = [9, 10]
        expected_ranges = [(5, 10)]
        self._assert_line_range(violations, expected_ranges)

    def test_one_line_file(self):
        self._init_src_file(1)
        violations = [1]
        expected_ranges = [(1, 1)]
        self._assert_line_range(violations, expected_ranges)

    def test_empty_file(self):
        self._init_src_file(0)
        violations = [0]
        expected_ranges = []
        self._assert_line_range(violations, expected_ranges)

    def test_no_violations(self):
        self._init_src_file(10)
        violations = []
        expected_ranges = []
        self._assert_line_range(violations, expected_ranges)

    def test_end_range_on_violation(self):
        self._init_src_file(40)

        # With context, the range for the snippet at 28 is 33
        # Expect that the snippet expands to include the violation
        # at the border.
        violations = [28, 33]
        expected_ranges = [(24, 37)]
        self._assert_line_range(violations, expected_ranges)

    def _compare_snippets_html_output(self, filename, violations, expected_out_filename):
        # Need to be in the fixture directory
        # so the source path is displayed correctly
        old_cwd = os.getcwd()
        self.addCleanup(lambda: os.chdir(old_cwd))
        os.chdir(fixture_path(''))

        # One higher-level test to make sure
        # the snippets are being rendered correctly
        snippets_html = '\n\n'.join(
            Snippet.load_snippets_html(filename, violations)
        )
        # Load the fixture for the expected contents
        expected_path = fixture_path(expected_out_filename)
        with io.open(expected_path, encoding='utf-8') as fixture_file:
            expected = fixture_file.read()
            if isinstance(expected, six.binary_type):
                expected = expected.decode('utf-8')

        # Check that we got what we expected
        assert_long_str_equal(expected, snippets_html, strip=True)

    def test_load_snippets_html(self):
        self._compare_snippets_html_output('snippet_src.py',
                                           [10, 12, 13, 50, 51, 54, 55, 57],
                                           'snippet_list.html')

    def test_load_utf8_snippets(self):
        self._compare_snippets_html_output('snippet_unicode.py',
                                           [10, 12, 13, 50, 51, 54, 55, 57],
                                           'snippet_unicode_html_output.html')

    def test_load_declared_arabic(self):
        self._compare_snippets_html_output('snippet_8859.py',
                                           [7],
                                           'snippet_arabic_output.html')

    def _assert_line_range(self, violation_lines, expected_ranges):
        """
        Assert that the snippets loaded using `violation_lines`
        have the correct ranges of lines.

        `violation_lines` is a list of line numbers containing violations
        (which should get included in snippets).

        `expected_ranges` is a list of `(start, end)` tuples representing
        the starting and ending lines expected in a snippet.
        Line numbers start at 1.
        """

        # Load snippets from the source file
        snippet_list = Snippet.load_snippets(
            self._src_path, violation_lines
        )

        # Check that we got the right number of snippets
        self.assertEqual(len(snippet_list), len(expected_ranges))

        # Check that the snippets have the desired ranges
        for snippet, line_range in zip(snippet_list, expected_ranges):

            # Expect that the line range is correct
            self.assertEqual(snippet.line_range(), line_range)

            # Expect that the source contents are correct
            start, end = line_range
            self.assertEqual(snippet.text(), self._src_lines(start, end))

    def _init_src_file(self, num_src_lines, src_path=None):
        """
        Write to the temporary file "Line 1", "Line 2", etc.
        up to `num_src_lines`.
        """
        # If no source path specified, use the temp file
        if src_path is None:
            src_path = self._src_path

        with open(src_path, 'w') as src_file:
            src_file.truncate()
            src_file.write(self._src_lines(1, num_src_lines))

    def _src_lines(self, start_line, end_line):
        """
        Test lines to write to the source file
        (Line 1, Line 2, ...).
        """
        return "\n".join([
            "Line {}".format(line_num)
            for line_num in range(start_line, end_line + 1)
        ])
