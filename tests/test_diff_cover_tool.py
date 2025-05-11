"""Test for diff_cover/diff_cover_tool."""

import pytest

from diff_cover.diff_cover_tool import parse_coverage_args


def test_parse_with_html_report():
    argv = ["reports/coverage.xml", "--format", "html:diff_cover.html"]
    arg_dict = parse_coverage_args(argv)

    assert arg_dict.get("coverage_file") == ["reports/coverage.xml"]
    assert arg_dict.get("format") == {"html": "diff_cover.html"}
    assert not arg_dict.get("ignore_unstaged")


def test_parse_with_no_report():
    argv = ["reports/coverage.xml"]
    arg_dict = parse_coverage_args(argv)

    assert arg_dict.get("coverage_file") == ["reports/coverage.xml"]
    assert arg_dict.get("format") == {}
    assert not arg_dict.get("ignore_unstaged")


def test_parse_with_multiple_reports():
    argv = [
        "reports/coverage.xml",
        "--format",
        "html:report.html,markdown:report.md",
    ]
    arg_dict = parse_coverage_args(argv)

    assert arg_dict.get("coverage_file") == ["reports/coverage.xml"]
    assert arg_dict.get("format") == {"html": "report.html", "markdown": "report.md"}
    assert not arg_dict.get("ignore_unstaged")


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
