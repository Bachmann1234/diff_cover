# pylint: disable=missing-function-docstring

"""Test for diff_cover.diff_quality - main"""

import pytest

from diff_cover.diff_quality_tool import main, parse_quality_args


def test_parse_with_html_report():
    argv = ["--violations", "pycodestyle", "--format", "html:diff_cover.html"]

    arg_dict = parse_quality_args(argv)

    assert arg_dict.get("violations") == "pycodestyle"
    assert arg_dict.get("format") == {"html": "diff_cover.html"}
    assert arg_dict.get("input_reports") == []
    assert not arg_dict.get("ignore_unstaged")
    assert arg_dict.get("diff_range_notation") == "..."


def test_parse_with_no_html_report():
    argv = ["--violations", "pylint"]

    arg_dict = parse_quality_args(argv)
    assert arg_dict.get("violations") == "pylint"
    assert arg_dict.get("input_reports") == []
    assert not arg_dict.get("ignore_unstaged")
    assert arg_dict.get("diff_range_notation") == "..."


def test_parse_with_one_input_report():
    argv = ["--violations", "pylint", "pylint_report.txt"]

    arg_dict = parse_quality_args(argv)
    assert arg_dict.get("input_reports") == ["pylint_report.txt"]


def test_parse_with_multiple_input_reports():
    argv = ["--violations", "pylint", "pylint_report_1.txt", "pylint_report_2.txt"]

    arg_dict = parse_quality_args(argv)
    assert arg_dict.get("input_reports") == [
        "pylint_report_1.txt",
        "pylint_report_2.txt",
    ]


def test_parse_with_options():
    argv = [
        "--violations",
        "pycodestyle",
        "--options=\"--exclude='*/migrations*'\"",
    ]
    arg_dict = parse_quality_args(argv)
    assert arg_dict.get("options") == "\"--exclude='*/migrations*'\""


def test_parse_with_ignored_unstaged():
    argv = ["--violations", "pylint", "--ignore-unstaged"]

    arg_dict = parse_quality_args(argv)
    assert arg_dict.get("ignore_unstaged")


def test_parse_invalid_arg():
    # No code quality test provided
    invalid_argv = [[], ["--html-report", "diff_cover.html"]]

    for argv in invalid_argv:
        with pytest.raises(SystemExit):
            parse_quality_args(argv)


def _test_parse_with_path_patterns(name):
    argv = ["--violations", "pep8"]
    arg_dict = parse_quality_args(argv)
    assert arg_dict.get("include") is None

    argv = ["--violations", "pep8", f"--{name}", "noneed/*.py"]
    arg_dict = parse_quality_args(argv)
    assert arg_dict.get(name) == ["noneed/*.py"]

    argv = ["--violations", "pep8", f"--{name}", "noneed/*.py", "other/**/*.py"]
    arg_dict = parse_quality_args(argv)
    assert arg_dict.get(name) == ["noneed/*.py", "other/**/*.py"]


def test_parse_with_exclude():
    _test_parse_with_path_patterns("exclude")


def test_parse_with_include():
    _test_parse_with_path_patterns("include")


def test_parse_diff_range_notation():
    argv = ["--violations", "pep8", "--diff-range-notation=.."]

    arg_dict = parse_quality_args(argv)

    assert arg_dict.get("violations") == "pep8"
    assert arg_dict.get("html_report") is None
    assert arg_dict.get("input_reports") == []
    assert not arg_dict.get("ignore_unstaged")
    assert arg_dict.get("diff_range_notation") == ".."


@pytest.fixture(autouse=True)
def patch_git_patch(mocker):
    mocker.patch("diff_cover.diff_quality_tool.GitPathTool")


@pytest.fixture
def report_mock(mocker):
    return mocker.patch(
        "diff_cover.diff_quality_tool.generate_quality_report", return_value=100
    )


def test_parse_options(report_mock):
    _run_main(
        report_mock,
        [
            "diff-quality",
            "--violations",
            "pylint",
            '--options="--foobar"',
        ],
    )


def test_parse_options_without_quotes(report_mock):
    _run_main(
        report_mock,
        [
            "diff-quality",
            "--violations",
            "pylint",
            "--options=--foobar",
        ],
    )


def _run_main(report, argv):
    main(argv)
    quality_reporter = report.call_args[0][0]
    assert quality_reporter.driver.name == "pylint"
    assert quality_reporter.options == "--foobar"
