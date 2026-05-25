# pylint: disable=missing-function-docstring

"""Test for diff_cover.snippets"""

import os

import pytest
from pygments.token import Token

from diff_cover.git_path import GitPathTool
from diff_cover.snippets import Snippet
from tests.helpers import fixture_path, load_fixture

SRC_TOKENS = [
    (Token.Comment, "# Test source"),
    (Token.Text, "\n"),
    (Token.Keyword, "def"),
    (Token.Text, " "),
    (Token.Name.Function, "test_func"),
    (Token.Punctuation, "("),
    (Token.Name, "arg"),
    (Token.Punctuation, ")"),
    (Token.Punctuation, ":"),
    (Token.Text, "\n"),
    (Token.Text, "    "),
    (Token.Keyword, "print"),
    (Token.Text, " "),
    (Token.Name, "arg"),
    (Token.Text, "\n"),
    (Token.Text, "    "),
    (Token.Keyword, "return"),
    (Token.Text, " "),
    (Token.Name, "arg"),
    (Token.Text, " "),
    (Token.Operator, "+"),
    (Token.Text, " "),
    (Token.Literal.Number.Integer, "5"),
    (Token.Text, "\n"),
]


def _assert_line_range(src_path, violation_lines, expected_ranges):
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
    snippet_list = Snippet.load_snippets(src_path, violation_lines)

    # Check that we got the right number of snippets
    assert len(snippet_list) == len(expected_ranges)

    # Check that the snippets have the desired ranges
    for snippet, line_range in zip(snippet_list, expected_ranges):
        # Expect that the line range is correct
        assert snippet.line_range() == line_range

        # Expect that the source contents are correct
        start, end = line_range
        assert snippet.text() == _src_lines(start, end)


def _src_lines(start_line, end_line):
    """
    Test lines to write to the source file
    (Line 1, Line 2, ...).
    """
    return "\n".join(
        [f"Line {line_num}" for line_num in range(start_line, end_line + 1)]
    )


def _assert_format(
    src_tokens,
    src_filename,
    start_line,
    last_line,
    violation_lines,
    expected_fixture,
):
    snippet = Snippet(
        src_tokens, src_filename, start_line, last_line, violation_lines, None
    )
    result = snippet.html()

    expected_str = load_fixture(expected_fixture, encoding="utf-8")

    assert expected_str.strip() == result.strip()
    assert isinstance(result, str)


def _compare_snippets_output(format_, filename, violations, expected_out_filename):
    # One higher-level test to make sure
    # the snippets are being rendered correctly
    formatted_snippets = Snippet.load_formatted_snippets(filename, violations)
    snippets_selected = "\n\n".join(formatted_snippets[format_])
    # Load the fixture for the expected contents
    expected_path = fixture_path(expected_out_filename)
    with open(expected_path, encoding="utf-8") as fixture_file:
        expected = fixture_file.read()
        if isinstance(expected, bytes):
            expected = expected.decode("utf-8")

    # Check that we got what we expected
    assert expected.strip() == snippets_selected.strip()


@pytest.fixture
def tmpfile(tmp_path):
    """
    Write to the temporary file "Line 1", "Line 2", etc.
    up to `num_src_lines`.
    """

    def _inner(num_src_lines):
        file = tmp_path / "src"
        file.write_text(_src_lines(1, num_src_lines))
        return str(file.resolve())

    return _inner


@pytest.fixture(autouse=True)
def patch_path_tool(mocker):
    # Path tool should not be aware of testing command
    mocker.patch.object(GitPathTool, "absolute_path", lambda path: path)
    mocker.patch.object(GitPathTool, "relative_path", lambda path: path)


@pytest.fixture
def switch_to_fixture_dir(request):
    # Need to be in the fixture directory
    # so the source path is displayed correctly
    os.chdir(fixture_path(""))
    yield
    os.chdir(request.config.invocation_dir)


def test_style_defs():
    style_str = Snippet.style_defs()
    expected_styles = load_fixture("snippet.css").strip()

    # Check that a sample of the styles are present
    # (use only a sample to make the test more robust
    # against Pygments changes).
    for expect_line in expected_styles.split("\n"):
        assert expect_line in style_str


def test_format():
    _assert_format(SRC_TOKENS, "test.py", 4, 6, [4, 6], "snippet_default.html")


def test_format_with_invalid_start_line():
    for start_line in [-2, -1, 0]:
        with pytest.raises(ValueError):
            Snippet("# test", "test.py", start_line, start_line + 1, [], None)


def test_format_with_invalid_violation_lines():
    # Violation lines outside the range of lines in the file
    # should be ignored.
    _assert_format(
        SRC_TOKENS,
        "test.py",
        1,
        2,
        [-1, 0, 5, 6],
        "snippet_invalid_violations.html",
    )


def test_no_filename_ext():
    # No filename extension: should default to text lexer
    _assert_format(SRC_TOKENS, "test", 4, 6, [4, 6], "snippet_no_filename_ext.html")


def test_unicode():
    unicode_src = [(Token.Text, "var = \u0123 \u5872 \u3389")]
    _assert_format(unicode_src, "test.py", 1, 2, [], "snippet_unicode.html")


def test_one_snippet(tmpfile):
    src_path = tmpfile(10)
    violations = [2, 3, 4, 5]
    expected_ranges = [(1, 9)]
    _assert_line_range(src_path, violations, expected_ranges)


def test_multiple_snippets(tmpfile):
    src_path = tmpfile(100)
    violations = [30, 31, 32, 35, 36, 60, 62]
    expected_ranges = [(26, 40), (56, 66)]
    _assert_line_range(src_path, violations, expected_ranges)


def test_no_lead_line(tmpfile):
    src_path = tmpfile(10)
    violations = [1, 2, 3]
    expected_ranges = [(1, 7)]
    _assert_line_range(src_path, violations, expected_ranges)


def test_no_lag_line(tmpfile):
    src_path = tmpfile(10)
    violations = [9, 10]
    expected_ranges = [(5, 10)]
    _assert_line_range(src_path, violations, expected_ranges)


def test_one_line_file(tmpfile):
    src_path = tmpfile(1)
    violations = [1]
    expected_ranges = [(1, 1)]
    _assert_line_range(src_path, violations, expected_ranges)


def test_empty_file(tmpfile):
    src_path = tmpfile(0)
    violations = [0]
    expected_ranges = []
    _assert_line_range(src_path, violations, expected_ranges)


def test_no_violations(tmpfile):
    src_path = tmpfile(10)
    violations = []
    expected_ranges = []
    _assert_line_range(src_path, violations, expected_ranges)


def test_load_snippets_no_violations_with_covered(tmpfile):
    """
    A fully-covered file (no violations) should still produce snippet
    ranges when `covered_lines` is supplied, expanded by the usual
    NUM_CONTEXT_LINES window.
    """
    src_path = tmpfile(10)
    snippets = Snippet.load_snippets(src_path, [], covered_lines=[5, 6])
    assert len(snippets) == 1
    # Lines 5 and 6 are interesting; expand by NUM_CONTEXT_LINES (4) on each
    # side, clamped to [1, num_src_lines].
    assert snippets[0].line_range() == (1, 10)


def test_html_marks_covered_lines():
    """
    When `covered_lines` is supplied, the rendered HTML should wrap each
    line in a `<span id=...>` and add the covered-line CSS class to spans
    whose line numbers are in `covered_lines`.
    """
    snippet = Snippet(
        SRC_TOKENS,
        "test.py",
        start_line=1,
        last_line=3,
        violation_lines=[3],
        lexer_name=None,
        covered_lines=[1, 2],
    )
    rendered = snippet.html()

    # Linespans should now be present, since covered_lines is non-empty.
    assert 'id="diff-cover-src-line-1"' in rendered
    assert 'id="diff-cover-src-line-2"' in rendered
    assert 'id="diff-cover-src-line-3"' in rendered

    # Lines 1 and 2 should be marked as covered.
    assert (
        f'<span id="diff-cover-src-line-1" class="{Snippet.COVERED_LINE_CSS_CLASS}">'
        in rendered
    )
    assert (
        f'<span id="diff-cover-src-line-2" class="{Snippet.COVERED_LINE_CSS_CLASS}">'
        in rendered
    )
    # Line 3 is a violation only and should NOT be marked covered.
    assert (
        f'<span id="diff-cover-src-line-3" class="{Snippet.COVERED_LINE_CSS_CLASS}">'
        not in rendered
    )
    # Violation highlighting (.hll) should still be present for line 3.
    assert "hll" in rendered


def test_html_without_covered_lines_keeps_legacy_output():
    """
    With no covered lines supplied, the rendered HTML must not include
    the new `linespans` per-line wrappers. This preserves byte-for-byte
    backwards compatibility with the historical HTML report output.
    """
    snippet = Snippet(
        SRC_TOKENS,
        "test.py",
        start_line=1,
        last_line=3,
        violation_lines=[3],
        lexer_name=None,
    )
    rendered = snippet.html()
    assert "diff-cover-src-line-" not in rendered
    assert Snippet.COVERED_LINE_CSS_CLASS not in rendered


def test_style_defs_includes_covered_class():
    style_str = Snippet.style_defs()
    assert Snippet.COVERED_LINE_CSS_CLASS in style_str
    assert Snippet.COVERED_COLOR in style_str


def test_html_marks_covered_lines_with_nonzero_start_line():
    """
    Pygments' `linespans` IDs use `linenostart`-based (file-absolute)
    line numbers, while `hl_lines` is snippet-relative. When the snippet
    does not start at line 1 we must NOT shift the covered line numbers
    when matching span IDs.
    """
    # Build a 5-line snippet covering source lines 58..62.
    src_tokens = [
        (Token.Text, "Line 58\n"),
        (Token.Text, "Line 59\n"),
        (Token.Text, "Line 60\n"),
        (Token.Text, "Line 61\n"),
        (Token.Text, "Line 62\n"),
    ]
    snippet = Snippet(
        src_tokens,
        "test.py",
        start_line=58,
        last_line=62,
        violation_lines=[60],
        lexer_name=None,
        covered_lines=[58, 59, 62],
    )
    rendered = snippet.html()

    # IDs are file-absolute (58..62), matching `linenostart`.
    assert 'id="diff-cover-src-line-58"' in rendered
    assert 'id="diff-cover-src-line-62"' in rendered

    # Covered lines should be tagged using their file-absolute IDs.
    for n in (58, 59, 62):
        assert (
            f'<span id="diff-cover-src-line-{n}" class="{Snippet.COVERED_LINE_CSS_CLASS}">'
            in rendered
        ), f"Expected covered-line class on line {n}"

    # Violation line (60) is in the middle of the snippet and must NOT
    # carry the covered class.
    assert (
        f'<span id="diff-cover-src-line-60" class="{Snippet.COVERED_LINE_CSS_CLASS}">'
        not in rendered
    )
    # Sanity-check: violation highlighting still applies. `hl_lines` is
    # snippet-relative, so line 60 is offset 3 within the snippet; the
    # `.hll` class should be present somewhere in the rendered HTML.
    assert "hll" in rendered


def test_end_range_on_violation(tmpfile):
    src_path = tmpfile(40)

    # With context, the range for the snippet at 28 is 33
    # Expect that the snippet expands to include the violation at the border
    violations = [28, 33]
    expected_ranges = [(24, 37)]
    _assert_line_range(src_path, violations, expected_ranges)


@pytest.mark.usefixtures("switch_to_fixture_dir")
def test_load_snippets_html():
    _compare_snippets_output(
        "html",
        "snippet_src.py",
        [10, 12, 13, 50, 51, 54, 55, 57],
        "snippet_list.html",
    )


@pytest.mark.usefixtures("switch_to_fixture_dir")
def test_load_snippets_markdown():
    _compare_snippets_output(
        "markdown",
        "snippet_src.py",
        [10, 12, 13, 50, 51, 54, 55, 57],
        "snippet_list.md",
    )
    _compare_snippets_output(
        "markdown",
        "snippet_src2.cpp",
        [4, 5],
        "snippet_list2.md",
    )
    _compare_snippets_output(
        "markdown",
        "snippet_src3.cpp",
        [12],
        "snippet_list3.md",
    )


@pytest.mark.usefixtures("switch_to_fixture_dir")
def test_load_utf8_snippets():
    _compare_snippets_output(
        "html",
        "snippet_unicode.py",
        [10, 12, 13, 50, 51, 54, 55, 57],
        "snippet_unicode_html_output.html",
    )


@pytest.mark.usefixtures("switch_to_fixture_dir")
def test_load_declared_arabic():
    _compare_snippets_output(
        "html", "snippet_8859.py", [7], "snippet_arabic_output.html"
    )


def test_latin_one_undeclared(tmp_path):
    file = tmp_path / "tmp"
    file.write_bytes("I am some latin 1 Â encoded text".encode("latin1"))

    contents = Snippet.load_contents(str(file))
    assert contents == "I am some latin 1 Â encoded text"
