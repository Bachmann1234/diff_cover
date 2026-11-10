# pylint: disable=missing-function-docstring

"""Test for diff_cover.diff_cover - main"""

import logging
import subprocess

import pytest

from diff_cover import diff_cover_tool
from diff_cover.diff_cover_tool import parse_coverage_args


def test_parse_coverage_file():
    argv = ["build/tests/coverage.xml", "--compare-branch=origin/other"]

    arg_dict = parse_coverage_args(argv)

    assert arg_dict["coverage_files"] == ["build/tests/coverage.xml"]
    assert arg_dict["compare_branch"] == "origin/other"
    assert arg_dict["diff_range_notation"] == "..."


def test_main_missing_coverage_file(tmp_path, monkeypatch, caplog):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "a.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t.t",
            "-c",
            "user.name=t",
            "commit",
            "-qm",
            "init",
        ],
        cwd=tmp_path,
        check=True,
    )
    monkeypatch.chdir(tmp_path)

    assert diff_cover_tool.main(["diff-cover", "missing.xml"]) == 1

    assert len(caplog.record_tuples) == 1
    logger_name, level, message = caplog.record_tuples[0]
    assert logger_name == "diff_cover.diff_cover_tool"
    assert level == logging.ERROR
    assert message.startswith("Couldn't read coverage file: ")


def test_parse_range_notation(capsys):
    argv = ["build/tests/coverage.xml", "--diff-range-notation=.."]

    arg_dict = parse_coverage_args(argv)

    assert arg_dict["coverage_files"] == ["build/tests/coverage.xml"]
    assert arg_dict["diff_range_notation"] == ".."

    with pytest.raises(SystemExit) as e:
        argv = ["build/tests/coverage.xml", "--diff-range-notation=FOO"]
        parse_coverage_args(argv)

    assert e.value.code == 2
    _, err = capsys.readouterr()
    assert "invalid choice: 'FOO'" in err
