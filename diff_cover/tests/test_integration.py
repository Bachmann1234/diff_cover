"""
High-level integration tests of diff-cover tool.
"""
from __future__ import unicode_literals

import os
import os.path
import re
import shutil
import tempfile
from collections import defaultdict
from io import BytesIO
from subprocess import Popen
from diff_cover.tests.helpers import unittest
import io
import six

from diff_cover.command_runner import CommandError
from diff_cover.git_path import GitPathTool
from diff_cover.tests.helpers import fixture_path, \
    assert_long_str_equal
from diff_cover.tool import main, QUALITY_DRIVERS
from diff_cover.violationsreporters.base import QualityDriver
from mock import patch, Mock


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
        cwd = os.getcwd()

        self._mock_popen = patch('subprocess.Popen').start()
        self._mock_sys = patch('diff_cover.tool.sys').start()
        try:
            self._mock_getcwd = patch('diff_cover.tool.os.getcwdu').start()
        except AttributeError:
            self._mock_getcwd = patch('diff_cover.tool.os.getcwd').start()
        self._git_root_path = cwd
        self._mock_getcwd.return_value = self._git_root_path

    def tearDown(self):
        """
        Undo all patches and reset the cwd
        """
        patch.stopall()
        os.chdir(self._old_cwd)

    def _clear_css(self, content):
        """
        The CSS is provided by pygments and changes fairly often.
        Im ok with simply saying "There was css"

        Perhaps I will eat these words
        """
        clean_content = re.sub("r'<style>.*</style>", content, '', re.DOTALL)
        assert len(content) > len(clean_content)
        return clean_content

    def _check_html_report(self, git_diff_path, expected_html_path, tool_args, expected_status=0, css_file=None):
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
        with io.open(git_diff_path, encoding='utf-8') as git_diff_file:
            self._set_git_diff_output(git_diff_file.read(), "")

        # Create a temporary directory to hold the output HTML report
        # Add a cleanup to ensure the directory gets deleted
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(temp_dir))
        html_report_path = os.path.join(temp_dir, 'diff_coverage.html')

        args = tool_args + ['--html-report', html_report_path]

        if css_file:
            css_file = os.path.join(temp_dir, css_file)
            args += ['--external-css-file', css_file]

        # Execute the tool
        code = main(args)
        self.assertEquals(code, expected_status)

        # Check the HTML report
        with io.open(expected_html_path, encoding='utf-8') as expected_file:
            with io.open(html_report_path, encoding='utf-8') as html_report:
                html = html_report.read()
                expected = expected_file.read()
                if css_file is None:
                    html = self._clear_css(html)
                    expected = self._clear_css(expected)
                assert_long_str_equal(expected, html, strip=True)

        return temp_dir

    def _check_console_report(self, git_diff_path, expected_console_path, tool_args, expected_status=0):
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
        with io.open(git_diff_path, encoding='utf-8') as git_diff_file:
            self._set_git_diff_output(git_diff_file.read(), "")

        # Capture stdout to a string buffer
        string_buffer = BytesIO()
        self._capture_stdout(string_buffer)

        # Execute the tool
        code = main(tool_args)

        self.assertEquals(code, expected_status)

        # Check the console report
        with open(expected_console_path) as expected_file:
            report = string_buffer.getvalue()
            expected = expected_file.read()
            assert_long_str_equal(expected, report, strip=True)

    def _capture_stdout(self, string_buffer):
        """
        Redirect output sent to `sys.stdout` to the BytesIO buffer
        `string_buffer`.
        """
        if six.PY3:
            self._mock_sys.stdout.buffer = string_buffer
        else:
            self._mock_sys.stdout = string_buffer

    def _set_git_diff_output(self, stdout, stderr):
        """
        Patch the call to `git diff` to output `stdout`
        and `stderr`.
        Patch the `git rev-parse` command to output
        a phony directory.
        """
        def patch_diff(command, **kwargs):
            if command[0:4] == ['git', '-c', 'diff.mnemonicprefix=no', 'diff']:
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

    def test_lua_coverage(self):
        """
        coverage report shows that diff-cover needs to normalize
        paths read in
        """
        self._check_console_report(
            'git_diff_lua.txt',
            'lua_console_report.txt',
            ['diff-cover', 'luacoverage.xml']
        )

    def test_fail_under_console(self):
        self._check_console_report(
            'git_diff_add.txt',
            'add_console_report.txt',
            ['diff-cover', 'coverage.xml', '--fail-under=90'],
            expected_status=1
        )

    def test_fail_under_pass_console(self):
        self._check_console_report(
            'git_diff_add.txt',
            'add_console_report.txt',
            ['diff-cover', 'coverage.xml', '--fail-under=5'],
            expected_status=0
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

    def test_fail_under_html(self):
        self._check_html_report(
            'git_diff_changed.txt',
            'changed_html_report.html',
            ['diff-cover', 'coverage.xml', '--fail-under=100.1'],
            expected_status=1
        )

    def test_fail_under_pass_html(self):
        self._check_html_report(
            'git_diff_changed.txt',
            'changed_html_report.html',
            ['diff-cover', 'coverage.xml', '--fail-under=100'],
            expected_status=0
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

    def test_subdir_coverage_html(self):
        """
        Assert that when diff-cover is ran from a subdirectory it
        generates correct reports.
        """
        old_cwd = self._mock_getcwd.return_value
        self._mock_getcwd.return_value = os.path.join(old_cwd, 'sub')
        self._check_html_report(
            'git_diff_subdir.txt',
            'subdir_coverage_html_report.html',
            ['diff-cover', 'coverage.xml']
        )
        self._mock_getcwd.return_value = old_cwd

    def test_subdir_coverage_console(self):
        """
        Assert that when diff-cover is ran from a subdirectory it
        generates correct reports.
        """
        old_cwd = self._mock_getcwd.return_value
        self._mock_getcwd.return_value = os.path.join(old_cwd, 'sub')
        self._check_console_report(
            'git_diff_subdir.txt',
            'subdir_coverage_console_report.txt',
            ['diff-cover', 'coverage.xml']
        )
        self._mock_getcwd.return_value = old_cwd

    def test_unicode_console(self):
        self._check_console_report(
            'git_diff_unicode.txt',
            'unicode_console_report.txt',
            ['diff-cover', 'unicode_coverage.xml']
        )

    def test_dot_net_diff(self):
        mock_path = '/code/samplediff/'
        self._mock_getcwd.return_value = mock_path
        with patch.object(GitPathTool, '_git_root', return_value=mock_path):
            self._check_console_report(
                'git_diff_dotnet.txt',
                'dotnet_coverage_console_report.txt',
                ['diff-cover', 'dotnet_coverage.xml']
            )

    def test_unicode_html(self):
        self._check_html_report(
            'git_diff_unicode.txt',
            'unicode_html_report.html',
            ['diff-cover', 'unicode_coverage.xml']
        )

    def test_html_with_external_css(self):
        temp_dir = self._check_html_report(
            'git_diff_external_css.txt',
            'external_css_html_report.html',
            ['diff-cover', 'coverage.xml'],
            css_file='external_style.css'
        )
        self.assertTrue(os.path.exists(os.path.join(temp_dir, 'external_style.css')))

    def test_git_diff_error(self):

        # Patch the output of `git diff` to return an error
        self._set_git_diff_output('', 'fatal error')

        # Expect an error
        with self.assertRaises(CommandError):
            main(['diff-cover', 'coverage.xml'])


class DiffQualityIntegrationTest(ToolsIntegrationBase):
    """
    High-level integration test.
    """

    def test_git_diff_error_diff_quality(self):

        # Patch the output of `git diff` to return an error
        self._set_git_diff_output('', 'fatal error')

        # Expect an error
        with self.assertRaises(CommandError):
            main(['diff-quality', '--violations', 'pep8'])

    def test_added_file_pep8_html(self):
        self._check_html_report(
            'git_diff_violations.txt',
            'pep8_violations_report.html',
            ['diff-quality', '--violations=pep8']
        )

    def test_added_file_pyflakes_html(self):
        self._check_html_report(
            'git_diff_violations.txt',
            'pyflakes_violations_report.html',
            ['diff-quality', '--violations=pyflakes']
        )

    def test_added_file_pylint_html(self):
        self._check_html_report(
            'git_diff_violations.txt',
            'pylint_violations_report.html',
            ['diff-quality', '--violations=pylint']
        )

    def test_fail_under_html(self):
        self._check_html_report(
            'git_diff_violations.txt',
            'pylint_violations_report.html',
            ['diff-quality', '--violations=pylint', '--fail-under=70'],
            expected_status=1
        )

    def test_fail_under_pass_html(self):
        self._check_html_report(
            'git_diff_violations.txt',
            'pylint_violations_report.html',
            ['diff-quality', '--violations=pylint', '--fail-under=40'],
            expected_status=0
        )

    def test_html_with_external_css(self):
        temp_dir = self._check_html_report(
            'git_diff_violations.txt',
            'pep8_violations_report_external_css.html',
            ['diff-quality', '--violations=pep8'],
            css_file='external_style.css'
        )
        self.assertTrue(os.path.exists(os.path.join(temp_dir, 'external_style.css')))

    def test_added_file_pep8_console(self):
        self._check_console_report(
            'git_diff_violations.txt',
            'pep8_violations_report.txt',
            ['diff-quality', '--violations=pep8']
        )

    def test_added_file_pep8_console_exclude_file(self):
        self._check_console_report(
            'git_diff_violations.txt',
            'empty_pep8_violations.txt',
            ['diff-quality', '--violations=pep8', '--options="--exclude=violations_test_file.py"']
        )

    def test_fail_under_console(self):
        self._check_console_report(
            'git_diff_violations.txt',
            'pyflakes_violations_report.txt',
            ['diff-quality', '--violations=pyflakes',
            '--fail-under=90'],
            expected_status=1
        )

    def test_fail_under_pass_console(self):
        self._check_console_report(
            'git_diff_violations.txt',
            'pyflakes_violations_report.txt',
            ['diff-quality', '--violations=pyflakes',
            '--fail-under=30'],
            expected_status=0
        )

    def test_added_file_pyflakes_console(self):
        self._check_console_report(
            'git_diff_violations.txt',
            'pyflakes_violations_report.txt',
            ['diff-quality', '--violations=pyflakes']
        )

    def test_added_file_pyflakes_console_two_files(self):
        self._check_console_report(
            'git_diff_violations_two_files.txt',
            'pyflakes_two_files.txt',
            ['diff-quality', '--violations=pyflakes']
        )

    def test_added_file_pylint_console(self):
        self._check_console_report(
            'git_diff_violations.txt',
            'pylint_violations_console_report.txt',
            ['diff-quality', '--violations=pylint'],
        )

    def test_pre_generated_pep8_report(self):

        # Pass in a pre-generated pep8 report instead of letting
        # the tool call pep8 itself.
        self._check_console_report(
            'git_diff_violations.txt',
            'pep8_violations_report.txt',
            ['diff-quality', '--violations=pep8', 'pep8_report.txt']
        )

    def test_pre_generated_pyflakes_report(self):

        # Pass in a pre-generated pyflakes report instead of letting
        # the tool call pyflakes itself.
        self._check_console_report(
            'git_diff_violations.txt',
            'pyflakes_violations_report.txt',
            ['diff-quality', '--violations=pyflakes', 'pyflakes_report.txt']
        )

    def test_pre_generated_pylint_report(self):

        # Pass in a pre-generated pylint report instead of letting
        # the tool call pylint itself.
        self._check_console_report(
            'git_diff_violations.txt',
            'pylint_violations_report.txt',
            ['diff-quality', '--violations=pylint', 'pylint_report.txt']
        )

    def test_pylint_report_with_dup_code_violation(self):
        self._check_console_report(
            'git_diff_code_dupe.txt',
            'pylint_dupe_violations_report.txt',
            ['diff-quality', '--violations=pylint', 'pylint_dupe.txt']
        )

    def _call_quality_expecting_error(self, tool_name, expected_error, report_arg='pylint_report.txt'):
        """
        Makes calls to diff_quality that should fail to ensure
        we get back the correct failure.
        Takes in a string which is a tool to call and
        an string which is the error you expect to see
        """
        with io.open('git_diff_add.txt', encoding='utf-8') as git_diff_file:
            self._set_git_diff_output(git_diff_file.read(), "")
        argv = ['diff-quality',
                '--violations={0}'.format(tool_name),
                report_arg]

        with patch('diff_cover.tool.LOGGER') as logger:
            exit_value = main(argv)
            logger.error.assert_called_with(expected_error)
            self.assertEqual(exit_value, 1)

    def test_tool_not_recognized(self):
        self._call_quality_expecting_error(
            'garbage',
            "Quality tool not recognized: "
            "'garbage'"
        )

    def test_tool_not_installed(self):
        # Pretend we support a tool named not_installed
        QUALITY_DRIVERS['not_installed'] = DoNothingDriver('not_installed', ['txt'], ['not_installed'])
        try:
            self._call_quality_expecting_error(
                'not_installed',
                "Quality tool not installed: "
                "'not_installed'",
                report_arg=''
            )
        finally:
            # Cleaning is good for the soul... and other tests
            del QUALITY_DRIVERS['not_installed']

    def test_do_nothing_reporter(self):
        # Pedantic, but really. This reporter
        # should not do anything
        # Does demonstrate a reporter can take in any tool
        # name though which is cool
        reporter = DoNothingDriver('pep8', [], [])
        self.assertEqual(reporter.parse_reports(''), {})


class DoNothingDriver(QualityDriver):
    """
    Dummy class that implements necessary abstract
    function
    """
    def __init__(self, name, supported_extensions, command):
        super(DoNothingDriver, self).__init__(name, supported_extensions, command)

    def parse_reports(self, parse_reports):
        return defaultdict(list)

    def installed(self):
        return False

