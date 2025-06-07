"""Test for diff_cover/diff_cover_tool."""

import argparse

import pytest

from diff_cover.diff_cover_tool import handle_old_format, parse_coverage_args


def test_parse_with_html_report():
    argv = ["reports/coverage.xml", "--format", "html:diff_cover.html"]
    arg_dict = parse_coverage_args(argv)

    assert arg_dict["coverage_files"] == ["reports/coverage.xml"]
    assert arg_dict["format"] == {"html": "diff_cover.html"}
    assert not arg_dict["ignore_unstaged"]


def test_report_path_with_colon():
    argv = [
        "reports/coverage.xml",
        "--format",
        "json:/this:path:should:work/without:breaking.json",
    ]
    arg_dict = parse_coverage_args(argv)
    assert arg_dict.get("format") == {
        "json": "/this:path:should:work/without:breaking.json"
    }


def test_parse_with_no_report():
    argv = ["reports/coverage.xml"]
    arg_dict = parse_coverage_args(argv)

    assert arg_dict["coverage_files"] == ["reports/coverage.xml"]
    assert arg_dict["format"] == {}
    assert not arg_dict["ignore_unstaged"]


def test_parse_with_multiple_reports():
    argv = [
        "reports/coverage.xml",
        "--format",
        "html:report.html,markdown:report.md",
    ]
    arg_dict = parse_coverage_args(argv)

    assert arg_dict["coverage_files"] == ["reports/coverage.xml"]
    assert arg_dict["format"] == {"html": "report.html", "markdown": "report.md"}
    assert not arg_dict["ignore_unstaged"]


def test_parse_with_multiple_old_reports(recwarn):
    argv = [
        "reports/coverage.xml",
        "--html-report",
        "report.html",
        "--markdown-report",
        "report.md",
        "--json-report",
        "report.json",
    ]
    arg_dict = parse_coverage_args(handle_old_format("desc", argv))

    assert arg_dict.get("format") == {
        "html": "report.html",
        "markdown": "report.md",
        "json": "report.json",
    }
    assert [str(w.message) for w in recwarn] == [
        "The --html-report option is deprecated. Use --format html:report.html instead.",
        "The --json-report option is deprecated. Use --format json:report.json instead.",
        "The --markdown-report option is deprecated. Use --format markdown:report.md instead.",
    ]


@pytest.mark.parametrize(
    ("old_report", "expected_error"),
    [
        (
            ["--html-report", "html", "--format", "html:report.html"],
            "Cannot use along with --format html",
        ),
        (
            ["--json-report", "json", "--format", "json:report.json"],
            "Cannot use along with --format json",
        ),
        (
            ["--markdown-report", "markdown", "--format", "markdown:report.md"],
            "Cannot use along with --format markdown",
        ),
    ],
)
def test_parse_mixing_new_with_old_reports(recwarn, old_report, expected_error):
    argv = [
        "reports/coverage.xml",
        *old_report,
    ]
    with pytest.raises(argparse.ArgumentError, match=expected_error):
        parse_coverage_args(handle_old_format("desc", argv))


def test_parse_with_ignored_unstaged():
    argv = ["reports/coverage.xml", "--ignore-unstaged"]
    arg_dict = parse_coverage_args(argv)

    assert arg_dict.get("ignore_unstaged")


def test_parse_invalid_arg():
    # No coverage XML report specified
    invalid_argv = [[], ["--format", "html:diff_cover.html"]]

    for argv in invalid_argv:
        with pytest.raises(SystemExit):
            parse_coverage_args(argv)


def _test_parse_with_path_patterns(name):
    argv = ["reports/coverage.xml"]
    arg_dict = parse_coverage_args(argv)
    assert arg_dict.get(f"{name}") is None

    argv = ["reports/coverage.xml", f"--{name}", "noneed/*"]
    arg_dict = parse_coverage_args(argv)
    assert arg_dict.get(f"{name}") == ["noneed/*"]

    argv = ["reports/coverage.xml", f"--{name}", "noneed/*", "other/**/*"]
    arg_dict = parse_coverage_args(argv)
    assert arg_dict.get(f"{name}") == ["noneed/*", "other/**/*"]


def test_parse_with_include():
    _test_parse_with_path_patterns("include")


def test_parse_with_exclude():
    _test_parse_with_path_patterns("exclude")
