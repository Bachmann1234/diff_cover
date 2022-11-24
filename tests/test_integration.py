# pylint: disable=attribute-defined-outside-init

"""High-level integration tests of diff-cover tool."""

import os
import os.path
import re
from collections import defaultdict
from io import BytesIO
from subprocess import Popen

import pytest

from diff_cover import diff_cover_tool, diff_quality_tool
from diff_cover.command_runner import CommandError
from diff_cover.git_path import GitPathTool
from diff_cover.violationsreporters.base import QualityDriver
from tests.helpers import fixture_path


class ToolsIntegrationBase:
    """Base class for diff-cover and diff-quality integration tests."""

    tool_module = None

    @pytest.fixture(autouse=True)
    def capture_fixtures(self, mocker, tmp_path):
        self.mocker = mocker
        self.tmp_path = tmp_path

    @pytest.fixture(autouse=True)
    def setup(self, mocker):
        """
        Patch the output of `git` commands and `os.getcwd`
        set the cwd to the fixtures dir
        """
        # Set the CWD to the fixtures dir
        old_cwd = os.getcwd()
        os.chdir(fixture_path(""))
        cwd = os.getcwd()

        self._mock_popen = mocker.patch("subprocess.Popen")
        self._mock_sys = mocker.patch(f"{self.tool_module}.sys")
        try:
            self._mock_getcwd = mocker.patch(f"{self.tool_module}.os.getcwdu")
        except AttributeError:
            self._mock_getcwd = mocker.patch(f"{self.tool_module}.os.getcwd")
        self._git_root_path = cwd
        self._mock_getcwd.return_value = self._git_root_path

        yield

        os.chdir(old_cwd)

    def _clear_css(self, content):
        """
        The CSS is provided by pygments and changes fairly often.
        Im ok with simply saying "There was css"

        Perhaps I will eat these words
        """
        clean_content = re.sub("r'<style>.*</style>", content, "", re.DOTALL)
        assert len(content) > len(clean_content)
        return clean_content

    def _check_html_report(
        self,
        git_diff_path,
        expected_html_path,
        tool_args,
        expected_status=0,
        css_file=None,
    ):
        """
        Verify that the tool produces the expected HTML report.

        `git_diff_path` is a path to a fixture containing the (patched) output of
        the call to `git diff`.

        `expected_console_path` is a path to the fixture containing
        the expected HTML output of the tool.

        `tool_args` is a list of command line arguments to pass
        to the tool.  You should include the name of the tool
        as the first argument.
        """

        # Patch the output of `git diff`
        with open(git_diff_path, encoding="utf-8") as git_diff_file:
            self._set_git_diff_output(git_diff_file.read(), "")

        # Create a temporary directory to hold the output HTML report
        # Add a cleanup to ensure the directory gets deleted
        temp_dir = self.tmp_path / "dummy"
        temp_dir.mkdir()

        html_report_path = os.path.join(temp_dir, "diff_coverage.html")

        args = tool_args + ["--html-report", html_report_path]

        if css_file:
            css_file = os.path.join(temp_dir, css_file)
            args += ["--external-css-file", css_file]

        # Execute the tool
        if "diff-cover" in args[0]:
            code = diff_cover_tool.main(args)
        else:
            code = diff_quality_tool.main(args)

        assert code == expected_status

        # Check the HTML report
        with open(expected_html_path, encoding="utf-8") as expected_file:
            with open(html_report_path, encoding="utf-8") as html_report:
                html = html_report.read()
                expected = expected_file.read()
                if css_file is None:
                    html = self._clear_css(html)
                    expected = self._clear_css(expected)
                assert expected.strip() == html.strip()

        return temp_dir

    def _check_console_report(
        self, git_diff_path, expected_console_path, tool_args, expected_status=0
    ):
        """
        Verify that the tool produces the expected console report.

        `git_diff_path` is a path to a fixture containing the (patched) output of
        the call to `git diff`.

        `expected_console_path` is a path to the fixture containing
        the expected console output of the tool.

        `tool_args` is a list of command line arguments to pass
        to the tool.  You should include the name of the tool
        as the first argument.
        """

        # Patch the output of `git diff`
        with open(git_diff_path, encoding="utf-8") as git_diff_file:
            self._set_git_diff_output(git_diff_file.read(), "")

        # Capture stdout to a string buffer
        string_buffer = BytesIO()
        self._capture_stdout(string_buffer)

        # Execute the tool
        if "diff-cover" in tool_args[0]:
            code = diff_cover_tool.main(tool_args)
        else:
            code = diff_quality_tool.main(tool_args)

        assert code == expected_status

        # Check the console report
        with open(expected_console_path) as expected_file:
            report = string_buffer.getvalue()
            expected = expected_file.read()
            assert expected.strip() == report.strip().decode("utf-8")

    def _capture_stdout(self, string_buffer):
        """
        Redirect output sent to `sys.stdout` to the BytesIO buffer
        `string_buffer`.
        """
        self._mock_sys.stdout.buffer = string_buffer

    def _set_git_diff_output(self, stdout, stderr, returncode=0):
        """
        Patch the call to `git diff` to output `stdout`
        and `stderr`.
        Patch the `git rev-parse` command to output
        a phony directory.
        """

        def patch_diff(command, **kwargs):
            if command[0:6] == [
                "git",
                "-c",
                "diff.mnemonicprefix=no",
                "-c",
                "diff.noprefix=no",
                "diff",
            ]:
                mock = self.mocker.Mock()
                mock.communicate.return_value = (stdout, stderr)
                mock.returncode = returncode
                return mock
            if command[0:2] == ["git", "rev-parse"]:
                mock = self.mocker.Mock()
                mock.communicate.return_value = (self._git_root_path, "")
                mock.returncode = returncode
                return mock

            return Popen(command, **kwargs)

        self._mock_popen.side_effect = patch_diff


class TestDiffCoverIntegration(ToolsIntegrationBase):
    """
    High-level integration test.
    The `git diff` is a mock, but everything else is our code.
    """

    tool_module = "diff_cover.diff_cover_tool"

    def test_added_file_html(self):
        self._check_html_report(
            "git_diff_add.txt", "add_html_report.html", ["diff-cover", "coverage.xml"]
        )

    def test_added_file_console(self):
        self._check_console_report(
            "git_diff_add.txt", "add_console_report.txt", ["diff-cover", "coverage.xml"]
        )

    def test_added_file_console_lcov(self):
        self._check_console_report(
            "git_diff_add.txt", "add_console_report.txt", ["diff-cover", "lcov.info"]
        )

    def test_lua_coverage(self):
        """
        coverage report shows that diff-cover needs to normalize
        paths read in
        """
        self._check_console_report(
            "git_diff_lua.txt",
            "lua_console_report.txt",
            ["diff-cover", "luacoverage.xml"],
        )

    def test_fail_under_console(self):
        self._check_console_report(
            "git_diff_add.txt",
            "add_console_report.txt",
            ["diff-cover", "coverage.xml", "--fail-under=90"],
            expected_status=1,
        )

    def test_fail_under_pass_console(self):
        self._check_console_report(
            "git_diff_add.txt",
            "add_console_report.txt",
            ["diff-cover", "coverage.xml", "--fail-under=5"],
            expected_status=0,
        )

    def test_deleted_file_html(self):
        self._check_html_report(
            "git_diff_delete.txt",
            "delete_html_report.html",
            ["diff-cover", "coverage.xml"],
        )

    def test_deleted_file_console(self):
        self._check_console_report(
            "git_diff_delete.txt",
            "delete_console_report.txt",
            ["diff-cover", "coverage.xml"],
        )

    def test_changed_file_html(self):
        self._check_html_report(
            "git_diff_changed.txt",
            "changed_html_report.html",
            ["diff-cover", "coverage.xml"],
        )

    def test_fail_under_html(self):
        self._check_html_report(
            "git_diff_changed.txt",
            "changed_html_report.html",
            ["diff-cover", "coverage.xml", "--fail-under=100.1"],
            expected_status=1,
        )

    def test_fail_under_pass_html(self):
        self._check_html_report(
            "git_diff_changed.txt",
            "changed_html_report.html",
            ["diff-cover", "coverage.xml", "--fail-under=100"],
            expected_status=0,
        )

    def test_changed_file_console(self):
        self._check_console_report(
            "git_diff_changed.txt",
            "changed_console_report.txt",
            ["diff-cover", "coverage.xml"],
        )

    def test_moved_file_html(self):
        self._check_html_report(
            "git_diff_moved.txt",
            "moved_html_report.html",
            ["diff-cover", "moved_coverage.xml"],
        )

    def test_moved_file_console(self):
        self._check_console_report(
            "git_diff_moved.txt",
            "moved_console_report.txt",
            ["diff-cover", "moved_coverage.xml"],
        )

    def test_mult_inputs_html(self):
        self._check_html_report(
            "git_diff_mult.txt",
            "mult_inputs_html_report.html",
            ["diff-cover", "coverage1.xml", "coverage2.xml"],
        )

    def test_mult_inputs_console(self):
        self._check_console_report(
            "git_diff_mult.txt",
            "mult_inputs_console_report.txt",
            ["diff-cover", "coverage1.xml", "coverage2.xml"],
        )

    def test_changed_file_lcov_console(self):
        self._check_console_report(
            "git_diff_changed.txt",
            "changed_console_report.txt",
            ["diff-cover", "lcov.info"],
        )

    def test_subdir_coverage_html(self):
        """
        Assert that when diff-cover is ran from a subdirectory it
        generates correct reports.
        """
        old_cwd = self._mock_getcwd.return_value
        self._mock_getcwd.return_value = os.path.join(old_cwd, "sub")
        self._check_html_report(
            "git_diff_subdir.txt",
            "subdir_coverage_html_report.html",
            ["diff-cover", "coverage.xml"],
        )
        self._mock_getcwd.return_value = old_cwd

    def test_subdir_coverage_console(self):
        """
        Assert that when diff-cover is ran from a subdirectory it
        generates correct reports.
        """
        old_cwd = self._mock_getcwd.return_value
        self._mock_getcwd.return_value = os.path.join(old_cwd, "sub")
        self._check_console_report(
            "git_diff_subdir.txt",
            "subdir_coverage_console_report.txt",
            ["diff-cover", "coverage.xml"],
        )
        self._mock_getcwd.return_value = old_cwd

    def test_unicode_console(self):
        self._check_console_report(
            "git_diff_unicode.txt",
            "unicode_console_report.txt",
            ["diff-cover", "unicode_coverage.xml"],
        )

    def test_dot_net_diff(self):
        mock_path = "/code/samplediff/"
        self._mock_getcwd.return_value = mock_path
        self.mocker.patch.object(GitPathTool, "_git_root", return_value=mock_path)
        self._check_console_report(
            "git_diff_dotnet.txt",
            "dotnet_coverage_console_report.txt",
            ["diff-cover", "dotnet_coverage.xml"],
        )

    def test_unicode_html(self):
        self._check_html_report(
            "git_diff_unicode.txt",
            "unicode_html_report.html",
            ["diff-cover", "unicode_coverage.xml"],
        )

    def test_html_with_external_css(self):
        temp_dir = self._check_html_report(
            "git_diff_external_css.txt",
            "external_css_html_report.html",
            ["diff-cover", "coverage.xml"],
            css_file="external_style.css",
        )
        assert os.path.exists(os.path.join(temp_dir, "external_style.css"))

    def test_git_diff_error(self):
        # Patch the output of `git diff` to return an error
        self._set_git_diff_output("", "fatal error", 1)

        # Expect an error
        with pytest.raises(CommandError):
            diff_cover_tool.main(["diff-cover", "coverage.xml"])

    def test_quiet_mode(self):
        self._check_console_report(
            "git_diff_violations.txt",
            "empty.txt",
            ["diff-cover", "coverage.xml", "-q"],
        )

    def test_show_uncovered_lines_console(self):
        self._check_console_report(
            "git_diff_add.txt",
            "show_uncovered_lines_console.txt",
            ["diff-cover", "--show-uncovered", "coverage.xml"],
        )


class TestDiffQualityIntegration(ToolsIntegrationBase):
    """
    High-level integration test.
    """

    tool_module = "diff_cover.diff_quality_tool"

    def test_git_diff_error_diff_quality(self):

        # Patch the output of `git diff` to return an error
        self._set_git_diff_output("", "fatal error", 1)

        # Expect an error
        with pytest.raises(CommandError):
            diff_quality_tool.main(["diff-quality", "--violations", "pycodestyle"])

    def test_added_file_pycodestyle_html(self):
        self._check_html_report(
            "git_diff_violations.txt",
            "pycodestyle_violations_report.html",
            ["diff-quality", "--violations=pycodestyle"],
        )

    def test_added_file_pyflakes_html(self):
        self._check_html_report(
            "git_diff_violations.txt",
            "pyflakes_violations_report.html",
            ["diff-quality", "--violations=pyflakes"],
        )

    def test_added_file_pylint_html(self):
        self._check_html_report(
            "git_diff_violations.txt",
            "pylint_violations_report.html",
            ["diff-quality", "--violations=pylint"],
        )

    def test_fail_under_html(self):
        self._check_html_report(
            "git_diff_violations.txt",
            "pylint_violations_report.html",
            ["diff-quality", "--violations=pylint", "--fail-under=80"],
            expected_status=1,
        )

    def test_fail_under_pass_html(self):
        self._check_html_report(
            "git_diff_violations.txt",
            "pylint_violations_report.html",
            ["diff-quality", "--violations=pylint", "--fail-under=40"],
            expected_status=0,
        )

    def test_html_with_external_css(self):
        temp_dir = self._check_html_report(
            "git_diff_violations.txt",
            "pycodestyle_violations_report_external_css.html",
            ["diff-quality", "--violations=pycodestyle"],
            css_file="external_style.css",
        )
        assert os.path.exists(os.path.join(temp_dir, "external_style.css"))

    def test_added_file_pycodestyle_console(self):
        self._check_console_report(
            "git_diff_violations.txt",
            "pycodestyle_violations_report.txt",
            ["diff-quality", "--violations=pycodestyle"],
        )

    def test_added_file_pycodestyle_console_exclude_file(self):
        self._check_console_report(
            "git_diff_violations.txt",
            "empty_pycodestyle_violations.txt",
            [
                "diff-quality",
                "--violations=pycodestyle",
                '--options="--exclude=violations_test_file.py"',
            ],
        )

    def test_fail_under_console(self):
        self._check_console_report(
            "git_diff_violations.txt",
            "pyflakes_violations_report.txt",
            ["diff-quality", "--violations=pyflakes", "--fail-under=90"],
            expected_status=1,
        )

    def test_fail_under_pass_console(self):
        self._check_console_report(
            "git_diff_violations.txt",
            "pyflakes_violations_report.txt",
            ["diff-quality", "--violations=pyflakes", "--fail-under=30"],
            expected_status=0,
        )

    def test_added_file_pyflakes_console(self):
        self._check_console_report(
            "git_diff_violations.txt",
            "pyflakes_violations_report.txt",
            ["diff-quality", "--violations=pyflakes"],
        )

    def test_added_file_pyflakes_console_two_files(self):
        self._check_console_report(
            "git_diff_violations_two_files.txt",
            "pyflakes_two_files.txt",
            ["diff-quality", "--violations=pyflakes"],
        )

    def test_added_file_pylint_console(self):
        console_report = "pylint_violations_console_report.txt"
        self._check_console_report(
            "git_diff_violations.txt",
            console_report,
            ["diff-quality", "--violations=pylint"],
        )

    def test_pre_generated_pycodestyle_report(self):

        # Pass in a pre-generated pycodestyle report instead of letting
        # the tool call pycodestyle itself.
        self._check_console_report(
            "git_diff_violations.txt",
            "pycodestyle_violations_report.txt",
            ["diff-quality", "--violations=pycodestyle", "pycodestyle_report.txt"],
        )

    def test_pre_generated_pyflakes_report(self):

        # Pass in a pre-generated pyflakes report instead of letting
        # the tool call pyflakes itself.
        self._check_console_report(
            "git_diff_violations.txt",
            "pyflakes_violations_report.txt",
            ["diff-quality", "--violations=pyflakes", "pyflakes_violations_report.txt"],
        )

    def test_pre_generated_pylint_report(self):

        # Pass in a pre-generated pylint report instead of letting
        # the tool call pylint itself.
        self._check_console_report(
            "git_diff_violations.txt",
            "pylint_violations_report.txt",
            ["diff-quality", "--violations=pylint", "pylint_report.txt"],
        )

    def test_pylint_report_with_dup_code_violation(self):
        self._check_console_report(
            "git_diff_code_dupe.txt",
            "pylint_dupe_violations_report.txt",
            ["diff-quality", "--violations=pylint", "pylint_dupe.txt"],
        )

    def _call_quality_expecting_error(
        self, tool_name, expected_error, report_arg="pylint_report.txt"
    ):
        """
        Makes calls to diff_quality that should fail to ensure
        we get back the correct failure.
        Takes in a string which is a tool to call and
        an string which is the error you expect to see
        """
        with open("git_diff_add.txt", encoding="utf-8") as git_diff_file:
            self._set_git_diff_output(git_diff_file.read(), "")
        argv = ["diff-quality", f"--violations={tool_name}"]
        if report_arg:
            argv.append(report_arg)

        logger = self.mocker.patch("diff_cover.diff_quality_tool.LOGGER")
        exit_value = diff_quality_tool.main(argv)
        logger.error.assert_called_with(*expected_error)
        assert exit_value == 1

    def test_tool_not_recognized(self):
        self._call_quality_expecting_error(
            "garbage", ("Quality tool not recognized: '%s'", "garbage"), "'garbage'"
        )

    def test_tool_not_installed(self):
        # Pretend we support a tool named not_installed
        self.mocker.patch.dict(
            diff_quality_tool.QUALITY_DRIVERS,
            {
                "not_installed": DoNothingDriver(
                    "not_installed", ["txt"], ["not_installed"]
                )
            },
        )

        self._call_quality_expecting_error(
            "not_installed",
            ("Failure: '%s'", "not_installed is not installed"),
            report_arg=None,
        )

    def test_do_nothing_reporter(self):
        # Pedantic, but really. This reporter
        # should not do anything
        # Does demonstrate a reporter can take in any tool
        # name though which is cool
        reporter = DoNothingDriver("pycodestyle", [], [])
        assert reporter.parse_reports("") == {}

    def test_quiet_mode(self):
        self._check_console_report(
            "git_diff_violations.txt",
            "empty.txt",
            ["diff-quality", "--violations=pylint", "-q"],
        )


class DoNothingDriver(QualityDriver):
    """Dummy class that implements necessary abstract functions."""

    def parse_reports(self, reports):
        return defaultdict(list)

    def installed(self):
        return False
