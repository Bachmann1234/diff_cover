"""
High-level integration tests of diff-cover tool.
"""
from __future__ import unicode_literals
from mock import patch, Mock
import os
import os.path
from subprocess import Popen
from six import StringIO
import tempfile
import shutil
from diff_cover.tool import main
from diff_cover.diff_reporter import GitDiffError
from diff_cover.tests.helpers import fixture_path, \
    assert_long_str_equal, unittest


class ToolsIntegrationBase(unittest.TestCase):
    """
    Base class for diff-cover and diff-quality integration tests
    """
    _old_cwd = None

    def setUp(self):
        """
        Patch the output of `git` commands and `os.getcwd`
        set the cwd to the fixtures dir
        """
        # Set the CWD to the fixtures dir
        self._old_cwd = os.getcwd()
        os.chdir(fixture_path(''))

        self._mock_popen = patch('subprocess.Popen').start()
        self._mock_sys = patch('diff_cover.tool.sys').start()
        self._mock_getcwd = patch('diff_cover.tool.os.getcwd').start()
        self._git_root_path = '/project/path'
        self._mock_getcwd.return_value = self._git_root_path

    def tearDown(self):
        """
        Undo all patches and reset the cwd
        """
        patch.stopall()
        os.chdir(self._old_cwd)

    def _check_html_report(self, git_diff_path, expected_html_path, tool_args):
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
        with open(git_diff_path) as git_diff_file:
            self._set_git_diff_output(git_diff_file.read(), "")

        # Create a temporary directory to hold the output HTML report
        # Add a cleanup to ensure the directory gets deleted
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(temp_dir))
        html_report_path = os.path.join(temp_dir, 'diff_coverage.html')

        # Patch the command-line arguments
        self._set_sys_args(tool_args + ['--html-report', html_report_path])

        # Execute the tool
        main()

        # Check the HTML report
        with open(expected_html_path) as expected_file:
            with open(html_report_path) as html_report:
                html = html_report.read()
                expected = expected_file.read()
                assert_long_str_equal(expected, html, strip=True)

    def _check_console_report(self, git_diff_path, expected_console_path, tool_args):
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
        with open(git_diff_path) as git_diff_file:
            self._set_git_diff_output(git_diff_file.read(), "")

        # Capture stdout to a string buffer
        string_buffer = StringIO()
        self._capture_stdout(string_buffer)

        # Patch sys.argv
        self._set_sys_args(tool_args)

        # Execute the tool
        main()

        # Check the console report
        with open(expected_console_path) as expected_file:
            report = string_buffer.getvalue()
            expected = expected_file.read()
            assert_long_str_equal(expected, report, strip=True)

    def _set_sys_args(self, argv):
        """
        Patch sys.argv with the argument array `argv`.
        """
        self._mock_sys.argv = argv

    def _capture_stdout(self, string_buffer):
        """
        Redirect output sent to `sys.stdout` to the StringIO buffer
        `string_buffer`.
        """
        self._mock_sys.stdout = string_buffer

    def _set_git_diff_output(self, stdout, stderr):
        """
        Patch the call to `git diff` to output `stdout`
        and `stderr`.
        Patch the `git rev-parse` command to output
        a phony directory.
        """
        def patch_diff(command, **kwargs):
            if command[0:2] == ['git', 'diff']:
                mock = Mock()
                mock.communicate.return_value = (stdout, stderr)
                return mock
            elif command[0:2] == ['git', 'rev-parse']:
                mock = Mock()
                mock.communicate.return_value = (self._git_root_path, '')
                return mock
            else:
                process = Popen(command, **kwargs)
                return process
        self._mock_popen.side_effect = patch_diff


class DiffCoverIntegrationTest(ToolsIntegrationBase):
    """
    High-level integration test.
    The `git diff` is a mock, but everything else is our code.
    """

    def test_added_file_html(self):
        self._check_html_report(
            'git_diff_add.txt',
            'add_html_report.html',
            ['diff-cover', 'coverage.xml']
        )

    def test_added_file_console(self):
        self._check_console_report(
            'git_diff_add.txt',
            'add_console_report.txt',
            ['diff-cover', 'coverage.xml']
        )

    def test_deleted_file_html(self):
        self._check_html_report(
            'git_diff_delete.txt',
            'delete_html_report.html',
            ['diff-cover', 'coverage.xml']
        )

    def test_deleted_file_console(self):
        self._check_console_report(
            'git_diff_delete.txt',
            'delete_console_report.txt',
            ['diff-cover', 'coverage.xml'],
        )

    def test_changed_file_html(self):
        self._check_html_report(
            'git_diff_changed.txt',
            'changed_html_report.html',
            ['diff-cover', 'coverage.xml']
        )

    def test_changed_file_console(self):
        self._check_console_report(
            'git_diff_changed.txt',
            'changed_console_report.txt',
            ['diff-cover', 'coverage.xml']
        )

    def test_moved_file_html(self):
        self._check_html_report(
            'git_diff_moved.txt',
            'moved_html_report.html',
            ['diff-cover', 'moved_coverage.xml']
        )

    def test_moved_file_console(self):
        self._check_console_report(
            'git_diff_moved.txt',
            'moved_console_report.txt',
            ['diff-cover', 'moved_coverage.xml']
        )

    def test_mult_inputs_html(self):
        self._check_html_report(
            'git_diff_mult.txt',
            'mult_inputs_html_report.html',
            ['diff-cover', 'coverage1.xml', 'coverage2.xml']
        )

    def test_mult_inputs_console(self):
        self._check_console_report(
            'git_diff_mult.txt',
            'mult_inputs_console_report.txt',
            ['diff-cover', 'coverage1.xml', 'coverage2.xml']
        )

    def test_git_diff_error(self):

        # Patch sys.argv
        self._set_sys_args(['diff-cover', 'coverage.xml'])

        # Patch the output of `git diff` to return an error
        self._set_git_diff_output('', 'fatal error')

        # Expect an error
        with self.assertRaises(GitDiffError):
            main()


class DiffQualityIntegrationTest(ToolsIntegrationBase):
    """
    High-level integration test.
    """

    def test_git_diff_error_diff_quality(self):

        # Patch sys.argv
        self._set_sys_args(['diff-quality', '--violations', 'pep8'])

        # Patch the output of `git diff` to return an error
        self._set_git_diff_output('', 'fatal error')

        # Expect an error
        with self.assertRaises(GitDiffError):
            main()

    def test_added_file_pep8_html(self):
        self._check_html_report(
            'git_diff_violations.txt',
            'pep8_violations_report.html',
            ['diff-quality', '--violations=pep8']
        )

    def test_added_file_pylint_html(self):
        self._check_html_report(
            'git_diff_violations.txt',
            'pylint_violations_report.html',
            ['diff-quality', '--violations=pylint']
        )

    def test_added_file_pep8_console(self):
        self._check_console_report(
            'git_diff_violations.txt',
            'pep8_violations_report.txt',
            ['diff-quality', '--violations=pep8']
        )

    def test_added_file_pylint_console(self):
        self._check_console_report(
            'git_diff_violations.txt',
            'pylint_violations_console_report.txt',
            ['diff-quality', '--violations=pylint'],
        )

    def test_pre_generated_pylint_report(self):

        # Pass in a pre-generated pylint report instead of letting
        # the tool call pylint itself.
        self._check_console_report(
            'git_diff_violations.txt',
            'pylint_violations_report.txt',
            ['diff-quality', '--violations=pylint', 'pylint_report.txt']
        )

    def test_pre_generated_pep8_report(self):

        # Pass in a pre-generated pep8 report instead of letting
        # the tool call pep8 itself.
        self._check_console_report(
            'git_diff_violations.txt',
            'pep8_violations_report.txt',
            ['diff-quality', '--violations=pep8', 'pep8_report.txt']
        )
