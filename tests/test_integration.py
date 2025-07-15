# pylint: disable=use-implicit-booleaness-not-comparison-to-zero
# pylint: disable=use-implicit-booleaness-not-comparison

"""High-level integration tests of diff-cover tool."""

import json
import os
import os.path
import re
import shutil
from collections import defaultdict
from pathlib import Path
from subprocess import Popen

import pytest

from diff_cover import diff_cover_tool, diff_quality_tool
from diff_cover.command_runner import CommandError
from diff_cover.git_path import GitPathTool
from diff_cover.violationsreporters.base import QualityDriver


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    src = Path(__file__).parent / "fixtures"
    temp_dir = tmp_path / "dummy"
    temp_dir.mkdir()

    shutil.copytree(src, tmp_path, dirs_exist_ok=True)
    monkeypatch.chdir(tmp_path)

    return temp_dir


@pytest.fixture
def patch_popen(mocker):
    return mocker.patch("subprocess.Popen")


@pytest.fixture
def patch_git_command(patch_popen, mocker):
    """
    Patch the call to `git diff` to output `stdout`
    and `stderr`.
    Patch the `git rev-parse` command to output
    a phony directory.
    """

    class Wrapper:
        def __init__(self):
            self.stdout = ""
            self.stderr = ""
            self.returncode = 0

        def set_stdout(self, value):
            if os.path.exists(value):
                with open(value, encoding="utf-8") as f:
                    self.stdout = f.read()
                    return
            self.stdout = value

        def set_stderr(self, value):
            if os.path.exists(value):
                with open(value, encoding="utf-8") as f:
                    self.stderr = f.read()
                    return
            self.stderr = value

        def set_returncode(self, value):
            self.returncode = value

    def patch_diff(command, **kwargs):
        if command[0:6] == [
            "git",
            "-c",
            "diff.mnemonicprefix=no",
            "-c",
            "diff.noprefix=no",
            "diff",
        ]:
            mock = mocker.Mock()
            mock.communicate.return_value = (helper.stdout, helper.stderr)
            mock.returncode = helper.returncode
            return mock
        if command[0:2] == ["git", "rev-parse"]:
            mock = mocker.Mock()
            mock.communicate.return_value = (os.getcwd(), "")
            mock.returncode = helper.returncode
            return mock

        return Popen(command, **kwargs)

    patch_popen.side_effect = patch_diff
    helper = Wrapper()

    return helper


def compare_html(expected_html_path, html_report_path, clear_inline_css=True):
    clean_content = re.compile("<style>.*</style>", flags=re.DOTALL)
    expected_file = open(expected_html_path, encoding="utf-8")
    html_report = open(html_report_path, encoding="utf-8")

    with expected_file, html_report:
        html = html_report.read()
        expected = expected_file.read()
        if clear_inline_css:
            # The CSS is provided by pygments and changes fairly often.
            # Im ok with simply saying "There was css"
            # Perhaps I will eat these words
            html = clean_content.sub("", html)
            expected = clean_content.sub("", expected)
        assert expected.strip() == html.strip()


def compare_markdown(expected_file_path, actual_file_path):
    expected_file = open(expected_file_path, encoding="utf-8")
    actual_file = open(actual_file_path, encoding="utf-8")
    with expected_file, actual_file:
        expected = expected_file.read()
        actual = actual_file.read()
        assert expected.strip() == actual.strip()


def compare_json(expected_json_path, actual_json_path):
    expected_file = open(expected_json_path, encoding="utf-8")
    actual_file = open(actual_json_path, encoding="utf-8")
    with expected_file, actual_file:
        expected = json.load(expected_file)
        actual = json.load(actual_file)
        assert expected == actual


def compare_console(expected_console_path, report):
    with open(expected_console_path, encoding="utf-8") as expected_file:
        expected = expected_file.read()
        assert expected.strip() == report.strip()


class TestDiffCoverIntegration:
    """
    High-level integration test.
    The `git diff` is a mock, but everything else is our code.
    """

    @pytest.fixture
    def runbin(self, cwd):
        del cwd  # fixtures cannot use pytest.mark.usefixtures
        return lambda x: diff_cover_tool.main(["diff-cover", *x])

    def test_added_file_html(self, runbin, patch_git_command):
        patch_git_command.set_stdout("git_diff_add.txt")
        assert (
            runbin(["coverage.xml", "--format", "html:dummy/diff_coverage.html"]) == 0
        )
        compare_html("add_html_report.html", "dummy/diff_coverage.html")

    def test_added_file_console(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_add.txt")
        assert runbin(["coverage.xml"]) == 0
        compare_console("add_console_report.txt", capsys.readouterr().out)

    def test_all_reports(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_add.txt")
        assert (
            runbin(
                [
                    "coverage.xml",
                    "--format",
                    "html:dummy/diff_coverage.html,"
                    "json:dummy/diff_coverage.json,"
                    "markdown:dummy/diff_coverage.md",
                ]
            )
            == 0
        )
        compare_console("add_console_report.txt", capsys.readouterr().out)
        compare_html("add_html_report.html", "dummy/diff_coverage.html")
        compare_json("add_json_report.json", "dummy/diff_coverage.json")
        compare_markdown("add_markdown_report.md", "dummy/diff_coverage.md")

    def test_added_file_console_lcov(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_add.txt")
        assert runbin(["lcov.info"]) == 0
        compare_console("add_console_report.txt", capsys.readouterr().out)

    def test_lua_coverage(self, runbin, patch_git_command, capsys):
        """
        coverage report shows that diff-cover needs to normalize
        paths read in
        """
        patch_git_command.set_stdout("git_diff_lua.txt")
        assert runbin(["luacoverage.xml"]) == 0
        compare_console("lua_console_report.txt", capsys.readouterr().out)

    def test_fail_under_console(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_add.txt")
        assert runbin(["coverage.xml", "--fail-under=90"]) == 1
        compare_console("add_console_report.txt", capsys.readouterr().out)

    def test_fail_under_pass_console(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_add.txt")
        assert runbin(["coverage.xml", "--fail-under=5"]) == 0
        compare_console("add_console_report.txt", capsys.readouterr().out)

    def test_deleted_file_html(self, runbin, patch_git_command):
        patch_git_command.set_stdout("git_diff_delete.txt")
        assert (
            runbin(["coverage.xml", "--format", "html:dummy/diff_coverage.html"]) == 0
        )
        compare_html("delete_html_report.html", "dummy/diff_coverage.html")

    def test_deleted_file_console(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_delete.txt")
        assert runbin(["coverage.xml"]) == 0
        compare_console("delete_console_report.txt", capsys.readouterr().out)

    def test_changed_file_html(self, runbin, patch_git_command):
        patch_git_command.set_stdout("git_diff_changed.txt")
        assert (
            runbin(["coverage.xml", "--format", "html:dummy/diff_coverage.html"]) == 0
        )
        compare_html("changed_html_report.html", "dummy/diff_coverage.html")

    def test_fail_under_html(self, runbin, patch_git_command):
        patch_git_command.set_stdout("git_diff_changed.txt")
        assert (
            runbin(
                [
                    "coverage.xml",
                    "--fail-under=100.1",
                    "--format",
                    "html:dummy/diff_coverage.html",
                ]
            )
            == 1
        )
        compare_html("changed_html_report.html", "dummy/diff_coverage.html")

    def test_fail_under_pass_html(self, runbin, patch_git_command):
        patch_git_command.set_stdout("git_diff_changed.txt")
        assert (
            runbin(
                [
                    "coverage.xml",
                    "--fail-under=100",
                    "--format",
                    "html:dummy/diff_coverage.html",
                ]
            )
            == 0
        )
        compare_html("changed_html_report.html", "dummy/diff_coverage.html")

    def test_changed_file_console(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_changed.txt")
        assert runbin(["coverage.xml"]) == 0
        compare_console("changed_console_report.txt", capsys.readouterr().out)

    def test_moved_file_html(self, runbin, patch_git_command):
        patch_git_command.set_stdout("git_diff_moved.txt")
        assert (
            runbin(["moved_coverage.xml", "--format", "html:dummy/diff_coverage.html"])
            == 0
        )
        compare_html("moved_html_report.html", "dummy/diff_coverage.html")

    def test_moved_file_console(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_moved.txt")
        assert runbin(["moved_coverage.xml"]) == 0
        compare_console("moved_console_report.txt", capsys.readouterr().out)

    def test_mult_inputs_html(self, runbin, patch_git_command):
        patch_git_command.set_stdout("git_diff_mult.txt")
        assert (
            runbin(
                [
                    "coverage1.xml",
                    "coverage2.xml",
                    "--format",
                    "html:dummy/diff_coverage.html",
                ]
            )
            == 0
        )
        compare_html("mult_inputs_html_report.html", "dummy/diff_coverage.html")

    def test_mult_inputs_console(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_mult.txt")
        assert runbin(["coverage1.xml", "coverage2.xml"]) == 0
        compare_console("mult_inputs_console_report.txt", capsys.readouterr().out)

    def test_changed_file_lcov_console(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_changed.txt")
        assert runbin(["lcov.info"]) == 0
        compare_console("changed_console_report.txt", capsys.readouterr().out)

    def test_subdir_coverage_html(self, runbin, mocker, patch_git_command):
        """
        Assert that when diff-cover is ran from a subdirectory it
        generates correct reports.
        """
        patch_git_command.set_stdout("git_diff_subdir.txt")
        mocker.patch.object(
            GitPathTool, "relative_path", wraps=lambda x: x.replace("sub/", "")
        )
        assert (
            runbin(["coverage.xml", "--format", "html:dummy/diff_coverage.html"]) == 0
        )
        compare_html("subdir_coverage_html_report.html", "dummy/diff_coverage.html")

    def test_subdir_coverage_console(self, runbin, mocker, patch_git_command, capsys):
        """
        Assert that when diff-cover is ran from a subdirectory it
        generates correct reports.
        """
        patch_git_command.set_stdout("git_diff_subdir.txt")
        mocker.patch.object(
            GitPathTool, "relative_path", wraps=lambda x: x.replace("sub/", "")
        )
        assert runbin(["coverage.xml"]) == 0
        compare_console("subdir_coverage_console_report.txt", capsys.readouterr().out)

    def test_unicode_console(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_unicode.txt")
        assert runbin(["unicode_coverage.xml"]) == 0
        compare_console("unicode_console_report.txt", capsys.readouterr().out)

    def test_dot_net_diff(self, mocker, runbin, patch_git_command, capsys):
        mocker.patch.object(GitPathTool, "_git_root", return_value="/code/samplediff/")
        patch_git_command.set_stdout("git_diff_dotnet.txt")
        assert runbin(["dotnet_coverage.xml"]) == 0
        compare_console("dotnet_coverage_console_report.txt", capsys.readouterr().out)

    def test_unicode_html(self, runbin, patch_git_command):
        patch_git_command.set_stdout("git_diff_unicode.txt")
        assert (
            runbin(
                ["unicode_coverage.xml", "--format", "html:dummy/diff_coverage.html"]
            )
            == 0
        )
        compare_html("unicode_html_report.html", "dummy/diff_coverage.html")

    def test_html_with_external_css(self, runbin, patch_git_command):
        patch_git_command.set_stdout("git_diff_external_css.txt")
        assert (
            runbin(
                [
                    "coverage.xml",
                    "--format",
                    "html:dummy/diff_coverage.html",
                    "--external-css-file",
                    "dummy/external_style.css",
                ]
            )
            == 0
        )
        assert Path("dummy/external_style.css").exists()

    def test_git_diff_error(self, runbin, patch_git_command):
        # Patch the output of `git diff` to return an error
        patch_git_command.set_stderr("fatal error")
        patch_git_command.set_returncode(1)
        # Expect an error
        with pytest.raises(CommandError):
            runbin(["coverage.xml"])

    def test_quiet_mode(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_violations.txt")
        assert runbin(["coverage.xml", "-q"]) == 0
        compare_console("empty.txt", capsys.readouterr().out)

    def test_show_uncovered_lines_console(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_add.txt")
        assert runbin(["--show-uncovered", "coverage.xml"]) == 0
        compare_console("show_uncovered_lines_console.txt", capsys.readouterr().out)

    def test_multiple_lcov_xml_reports(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_add.txt")
        with pytest.raises(
            ValueError, match="Mixing LCov and XML reports is not supported yet"
        ):
            runbin(["--show-uncovered", "coverage.xml", "lcov.info"])

    def test_expand_coverage_report_complete_report(
        self, runbin, patch_git_command, capsys
    ):
        patch_git_command.set_stdout("git_diff_add.txt")
        assert runbin(["coverage.xml", "--expand-coverage-report"]) == 0
        compare_console("add_console_report.txt", capsys.readouterr().out)

    def test_expand_coverage_report_uncomplete_report(
        self, runbin, patch_git_command, capsys
    ):
        patch_git_command.set_stdout("git_diff_add.txt")
        assert runbin(["coverage_missing_lines.xml", "--expand-coverage-report"]) == 0
        compare_console("expand_console_report.txt", capsys.readouterr().out)

    def test_real_world_cpp_lcov_coverage(self, runbin, patch_git_command, capsys):
        """Test with real C++ LCOV coverage data"""
        # Create git diff for C++ files
        patch_git_command.set_stdout("git_diff_cpp.txt")

        # Use real C++ LCOV data
        assert runbin(["real_cpp_coverage.lcov"]) == 0

        # Compare output with expected result
        compare_console("real_cpp_console_report.txt", capsys.readouterr().out)

    def test_real_world_python_lcov_coverage(self, runbin, patch_git_command, capsys):
        """Test with real Python LCOV coverage data with checksums"""
        # Create git diff for Python files
        patch_git_command.set_stdout("git_diff_python.txt")

        # Use real Python LCOV data
        assert runbin(["real_python_coverage.lcov"]) == 0

        # Compare output with expected result
        compare_console("real_python_console_report.txt", capsys.readouterr().out)

    def test_real_world_typescript_lcov_coverage(
        self, runbin, patch_git_command, capsys
    ):
        """Test with real TypeScript LCOV coverage data with branch coverage"""
        # Create git diff for TypeScript files
        patch_git_command.set_stdout("git_diff_typescript.txt")

        # Use real TypeScript LCOV data
        assert runbin(["real_typescript_coverage.lcov"]) == 0

        # Compare output with expected result
        compare_console("real_typescript_console_report.txt", capsys.readouterr().out)

    def test_real_world_lcov_with_function_coverage(
        self, runbin, patch_git_command, capsys
    ):
        """Test LCOV parsing with function coverage data (C++ format)"""
        # Create git diff for C++ files with FNL/FNA directives
        patch_git_command.set_stdout("git_diff_cpp_functions.txt")

        # Use LCOV data with FNL/FNA directives
        assert runbin(["cpp_functions_coverage.lcov"]) == 0

        # Compare output with expected result
        compare_console("cpp_functions_console_report.txt", capsys.readouterr().out)

    def test_real_world_lcov_with_branch_coverage(
        self, runbin, patch_git_command, capsys
    ):
        """Test LCOV parsing with branch coverage data (TypeScript format)"""
        # Create git diff for TypeScript files with branch coverage
        patch_git_command.set_stdout("git_diff_typescript_branches.txt")

        # Use LCOV data with BRDA directives
        assert runbin(["typescript_branches_coverage.lcov"]) == 0

        # Compare output with expected result
        compare_console(
            "typescript_branches_console_report.txt", capsys.readouterr().out
        )


class TestDiffQualityIntegration:
    """
    High-level integration test.
    """

    @pytest.fixture
    def runbin(self, cwd):
        del cwd  # fixtures cannot use pytest.mark.usefixtures
        return lambda x: diff_quality_tool.main(["diff-quality", *x])

    def test_git_diff_error_diff_quality(self, runbin, patch_git_command):
        # Patch the output of `git diff` to return an error
        patch_git_command.set_stderr("fatal error")
        patch_git_command.set_returncode(1)
        # Expect an error
        with pytest.raises(CommandError):
            runbin(["coverage.xml", "--violations", "pycodestyle"])

    def test_added_file_pycodestyle_html(self, runbin, patch_git_command):
        patch_git_command.set_stdout("git_diff_violations.txt")
        assert (
            runbin(
                [
                    "--format",
                    "html:dummy/diff_coverage.html",
                    "--violations=pycodestyle",
                ]
            )
            == 0
        )
        compare_html("pycodestyle_violations_report.html", "dummy/diff_coverage.html")

    def test_all_reports(self, runbin, patch_git_command):
        patch_git_command.set_stdout("git_diff_violations.txt")
        assert (
            runbin(
                [
                    "--violations=pycodestyle",
                    "--format",
                    "html:dummy/diff_coverage.html,"
                    "json:dummy/diff_coverage.json,"
                    "markdown:dummy/diff_coverage.md",
                ]
            )
            == 0
        )
        compare_html("pycodestyle_violations_report.html", "dummy/diff_coverage.html")
        compare_json("pycodestyle_violations_report.json", "dummy/diff_coverage.json")
        compare_markdown("pycodestyle_violations_report.md", "dummy/diff_coverage.md")

    def test_added_file_pyflakes_html(self, runbin, patch_git_command):
        patch_git_command.set_stdout("git_diff_violations.txt")
        assert (
            runbin(
                ["--violations=pyflakes", "--format", "html:dummy/diff_coverage.html"]
            )
            == 0
        )
        compare_html("pyflakes_violations_report.html", "dummy/diff_coverage.html")

    def test_added_file_pylint_html(self, runbin, patch_git_command):
        patch_git_command.set_stdout("git_diff_violations.txt")
        assert (
            runbin(["--violations=pylint", "--format", "html:dummy/diff_coverage.html"])
            == 0
        )
        compare_html("pylint_violations_report.html", "dummy/diff_coverage.html")

    def test_fail_under_html(self, runbin, patch_git_command):
        patch_git_command.set_stdout("git_diff_violations.txt")
        assert (
            runbin(
                [
                    "--violations=pylint",
                    "--fail-under=80",
                    "--format",
                    "html:dummy/diff_coverage.html",
                ]
            )
            == 1
        )
        compare_html("pylint_violations_report.html", "dummy/diff_coverage.html")

    def test_fail_under_pass_html(self, runbin, patch_git_command):
        patch_git_command.set_stdout("git_diff_violations.txt")
        assert (
            runbin(
                [
                    "--violations=pylint",
                    "--fail-under=40",
                    "--format",
                    "html:dummy/diff_coverage.html",
                ]
            )
            == 0
        )
        compare_html("pylint_violations_report.html", "dummy/diff_coverage.html")

    def test_html_with_external_css(self, runbin, patch_git_command):
        patch_git_command.set_stdout("git_diff_violations.txt")
        assert (
            runbin(
                [
                    "--violations=pycodestyle",
                    "--format",
                    "html:dummy/diff_coverage.html",
                    "--external-css-file",
                    "dummy/external_style.css",
                ]
            )
            == 0
        )
        compare_html(
            "pycodestyle_violations_report_external_css.html",
            "dummy/diff_coverage.html",
            clear_inline_css=False,
        )
        assert Path("dummy/external_style.css").exists()

    def test_added_file_pycodestyle_console(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_violations.txt")
        assert runbin(["--violations=pycodestyle"]) == 0
        compare_console("pycodestyle_violations_report.txt", capsys.readouterr().out)

    def test_added_file_pycodestyle_console_exclude_file(
        self, runbin, patch_git_command, capsys
    ):
        patch_git_command.set_stdout("git_diff_violations.txt")
        assert (
            runbin(
                [
                    "--violations=pycodestyle",
                    '--options="--exclude=violations_test_file.py"',
                ]
            )
            == 0
        )
        compare_console("empty_pycodestyle_violations.txt", capsys.readouterr().out)

    def test_fail_under_console(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_violations.txt")
        assert runbin(["--violations=pyflakes", "--fail-under=90"]) == 1
        compare_console("pyflakes_violations_report.txt", capsys.readouterr().out)

    def test_fail_under_pass_console(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_violations.txt")
        assert runbin(["--violations=pyflakes", "--fail-under=30"]) == 0
        compare_console("pyflakes_violations_report.txt", capsys.readouterr().out)

    def test_added_file_pyflakes_console(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_violations.txt")
        assert runbin(["--violations=pyflakes"]) == 0
        compare_console("pyflakes_violations_report.txt", capsys.readouterr().out)

    def test_added_file_pyflakes_console_two_files(
        self, runbin, patch_git_command, capsys
    ):
        patch_git_command.set_stdout("git_diff_violations_two_files.txt")
        assert runbin(["--violations=pyflakes"]) == 0
        compare_console("pyflakes_two_files.txt", capsys.readouterr().out)

    def test_added_file_pylint_console(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_violations.txt")
        assert runbin(["--violations=pylint"]) == 0
        compare_console("pylint_violations_console_report.txt", capsys.readouterr().out)

    def test_pre_generated_pycodestyle_report(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_violations.txt")
        # Pass in a pre-generated pycodestyle report instead of letting
        # the tool call pycodestyle itself.
        assert runbin(["--violations=pycodestyle", "pycodestyle_report.txt"]) == 0
        compare_console("pycodestyle_violations_report.txt", capsys.readouterr().out)

    def test_pre_generated_pyflakes_report(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_violations.txt")
        # Pass in a pre-generated pyflakes report instead of letting
        # the tool call pyflakes itself.
        assert runbin(["--violations=pyflakes", "pyflakes_violations_report.txt"]) == 0
        compare_console("pyflakes_violations_report.txt", capsys.readouterr().out)

    def test_pre_generated_pylint_report(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_violations.txt")
        # Pass in a pre-generated pylint report instead of letting
        # the tool call pylint itself.
        assert runbin(["--violations=pylint", "pylint_report.txt"]) == 0
        compare_console("pylint_violations_report.txt", capsys.readouterr().out)

    def test_pylint_report_with_dup_code_violation(
        self, runbin, patch_git_command, capsys
    ):
        patch_git_command.set_stdout("git_diff_code_dupe.txt")
        assert runbin(["--violations=pylint", "pylint_dupe.txt"]) == 0
        compare_console("pylint_dupe_violations_report.txt", capsys.readouterr().out)

    def test_tool_not_recognized(self, runbin, patch_git_command, mocker):
        patch_git_command.set_stdout("git_diff_violations.txt")
        logger = mocker.patch("diff_cover.diff_quality_tool.LOGGER")
        assert runbin(["--violations=garbage", "pylint_report.txt"]) == 1
        logger.error.assert_called_with("Quality tool not recognized: '%s'", "garbage")

    def test_tool_not_installed(self, mocker, runbin, patch_git_command):
        # Pretend we support a tool named not_installed
        mocker.patch.dict(
            diff_quality_tool.QUALITY_DRIVERS,
            {
                "not_installed": DoNothingDriver(
                    "not_installed", ["txt"], ["not_installed"]
                )
            },
        )
        patch_git_command.set_stdout("git_diff_add.txt")
        logger = mocker.patch("diff_cover.diff_quality_tool.LOGGER")
        assert runbin(["--violations=not_installed"]) == 1
        logger.error.assert_called_with(
            "Failure: '%s'", "not_installed is not installed"
        )

    def test_do_nothing_reporter(self):
        # Pedantic, but really. This reporter
        # should not do anything
        # Does demonstrate a reporter can take in any tool
        # name though which is cool
        reporter = DoNothingDriver("pycodestyle", [], [])
        assert reporter.parse_reports("") == {}

    def test_quiet_mode(self, runbin, patch_git_command, capsys):
        patch_git_command.set_stdout("git_diff_violations.txt")
        assert runbin(["--violations=pylint", "-q"]) == 0
        compare_console("empty.txt", capsys.readouterr().out)


class DoNothingDriver(QualityDriver):
    """Dummy class that implements necessary abstract functions."""

    def parse_reports(self, reports):
        return defaultdict(list)

    def installed(self):
        return False
