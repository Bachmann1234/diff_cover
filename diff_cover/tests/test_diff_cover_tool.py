"""Test for diff_cover/diff_cover_tool."""

import pytest

from diff_cover.diff_cover_tool import parse_coverage_args


def test_parse_with_html_report():
    argv = ["reports/coverage.xml", "--html-report", "diff_cover.html"]

    arg_dict = parse_coverage_args(argv)

    assert arg_dict.get("coverage_xml") == ["reports/coverage.xml"]

    assert arg_dict.get("html_report") == "diff_cover.html"
    assert not arg_dict.get("ignore_unstaged")


def test_parse_with_no_html_report():
    argv = ["reports/coverage.xml"]

    arg_dict = parse_coverage_args(argv)
    assert arg_dict.get("coverage_xml") == ["reports/coverage.xml"]
    assert not arg_dict.get("ignore_unstaged")


def test_parse_with_ignored_unstaged():
    argv = ["reports/coverage.xml", "--ignore-unstaged"]

    arg_dict = parse_coverage_args(argv)
    assert arg_dict.get("ignore_unstaged")


def test_parse_invalid_arg():
    # No coverage XML report specified
    invalid_argv = [[], ["--html-report", "diff_cover.html"]]

    for argv in invalid_argv:
        with pytest.raises(SystemExit):
            parse_coverage_args(argv)


def test_parse_with_exclude():
    argv = ["reports/coverage.xml"]
    arg_dict = parse_coverage_args(argv)
    assert arg_dict.get("exclude") is None

    argv = ["reports/coverage.xml", "--exclude", "noneed/*.py"]

    arg_dict = parse_coverage_args(argv)
    assert arg_dict.get("exclude") == ["noneed/*.py"]

    argv = ["reports/coverage.xml", "--exclude", "noneed/*.py", "other/**/*.py"]

    arg_dict = parse_coverage_args(argv)
    assert arg_dict.get("exclude") == ["noneed/*.py", "other/**/*.py"]
