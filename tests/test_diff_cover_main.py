# pylint: disable=missing-function-docstring

"""Test for diff_cover.diff_cover - main"""

import pytest

from diff_cover.diff_cover_tool import parse_coverage_args


def test_parse_coverage_file():
    argv = ["build/tests/coverage.xml", "--compare-branch=origin/other"]

    arg_dict = parse_coverage_args(argv)

    assert arg_dict["coverage_file"] == ["build/tests/coverage.xml"]
    assert arg_dict["compare_branch"] == "origin/other"
    assert arg_dict["diff_range_notation"] == "..."


def test_parse_range_notation(capsys):
    argv = ["build/tests/coverage.xml", "--diff-range-notation=.."]

    arg_dict = parse_coverage_args(argv)

    assert arg_dict["coverage_file"] == ["build/tests/coverage.xml"]
    assert arg_dict["diff_range_notation"] == ".."

    with pytest.raises(SystemExit) as e:
        argv = ["build/tests/coverage.xml", "--diff-range-notation=FOO"]
        parse_coverage_args(argv)

    assert e.value.code == 2
    _, err = capsys.readouterr()
    assert "invalid choice: 'FOO'" in err
