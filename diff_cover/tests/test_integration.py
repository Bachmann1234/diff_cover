"""
High-level integration tests of diff-cover tool.
"""

from mock import patch, Mock
import os
import os.path
from subprocess import Popen
from StringIO import StringIO
import tempfile
import shutil
from diff_cover.tool import main
from diff_cover.diff_reporter import GitDiffError
from diff_cover.tests.helpers import unittest


class ToolsIntegrationBase(unittest.TestCase):
    """
    Base class for diff-cover and diff-quality integration tests
    """
    _old_cwd = None

    def setUp(self):
        """
        Patch the output of `git diff` and set the cwd to the fixtures dir
        """
        self._mock_popen = patch('subprocess.Popen').start()
        self._mock_sys = patch('diff_cover.tool.sys').start()

        # Set the CWD to the fixtures dir
        self._old_cwd = os.getcwd()
        os.chdir(self._fixture_path())

    def tearDown(self):
        """
        Undo all patches and reset the cwd
        """
        patch.stopall()
        os.chdir(self._old_cwd)

    def _check_html_report(self, git_diff_path, coverage_xml_paths,
                           expected_html_path, quality_reporter='pep8'):
        """
        If `coverage_xml_paths` is not empty, assert that given `git_diff_path`
        and `coverage_xml_paths`, diff-cover generates the expected HTML report.

        If `coverage_xml_paths` is empty, asserts that given `git_diff_path` and
        `quality_reporter` generates the expected HTML report.
        """

        # Patch the output of `git diff`
        with open(git_diff_path) as git_diff_file:
            self._set_git_diff_output(git_diff_file.read(), "")

        # Create a temporary directory to hold the output HTML report
        # Add a cleanup to ensure the directory gets deleted
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(temp_dir))
        html_report_path = os.path.join(temp_dir, 'diff_coverage.html')


        if len(coverage_xml_paths) > 0:
            input_list = ['diff-cover'] + coverage_xml_paths + ['--html-report', html_report_path]
            self._set_sys_args(input_list)

        else:
            self._set_sys_args(['diff-quality',
                                '--violations', quality_reporter,
                                '--html-report', html_report_path])

        # Run diff-cover or diff-quality, as specified
        main()

        # Check the HTML report
        with open(expected_html_path) as expected_file:
            with open(html_report_path) as html_report:
                html = html_report.read()
                expected = expected_file.read()
                self.assertEqual(html, expected)

    def _check_console_report(self, git_diff_path, coverage_xml_paths,
                              expected_console_path, quality_reporter='pep8'):
        """
        If `coverage_xml_paths` is not empty, assert that given `git_diff_path`
        and `coverage_xml_paths`, diff-cover generates the expected console report.

        If `coverage_xml_paths` is empty, asserts that given `git_diff_path` and
        `quality_reporter` generates the expected console report.
        """

        # Patch the output of `git diff`
        with open(git_diff_path) as git_diff_file:
            self._set_git_diff_output(git_diff_file.read(), "")

        # Capture stdout to a string buffer
        string_buffer = StringIO()
        self._capture_stdout(string_buffer)

        # Patch sys.argv
        if len(coverage_xml_paths) > 0:
            input_list = ['diff-cover'] + coverage_xml_paths
            self._set_sys_args(input_list)
        else:
            self._set_sys_args(['diff-quality',
                                '--violations', quality_reporter])

        # Run diff-cover or diff-quality, as specified
        main()

        # Check the console report
        with open(expected_console_path) as expected_file:
            report = string_buffer.getvalue()
            expected = expected_file.read()
            self.assertEqual(report, expected)

    def _fixture_path(self):
        """
        Return an absolute path to the the test fixture directory
        """
        return os.path.join(os.path.dirname(__file__), 'fixtures')

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
        """
        def patch_diff(command, **kwargs):
            if command[0] == 'git':
                mock = Mock()
                mock.communicate.return_value = (stdout, stderr)
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
        self._check_html_report('git_diff_add.txt',
                                ['coverage.xml'],
                                'add_html_report.html')

    def test_added_file_console(self):
        self._check_console_report('git_diff_add.txt',
                                   ['coverage.xml'],
                                   'add_console_report.txt')

    def test_deleted_file_html(self):
        self._check_html_report('git_diff_delete.txt',
                                ['coverage.xml'],
                                'delete_html_report.html')

    def test_deleted_file_console(self):
        self._check_console_report('git_diff_delete.txt',
                                   ['coverage.xml'],
                                   'delete_console_report.txt')

    def test_changed_file_html(self):
        self._check_html_report('git_diff_changed.txt',
                                ['coverage.xml'],
                                'changed_html_report.html')

    def test_changed_file_console(self):
        self._check_console_report('git_diff_changed.txt',
                                   ['coverage.xml'],
                                   'changed_console_report.txt')

    def test_moved_file_html(self):
        self._check_html_report('git_diff_moved.txt',
                                ['moved_coverage.xml'],
                                'moved_html_report.html')

    def test_moved_file_console(self):
        self._check_console_report('git_diff_moved.txt',
                                   ['moved_coverage.xml'],
                                   'moved_console_report.txt')

    def test_mult_inputs_html(self):
        self._check_html_report('git_diff_mult.txt',
                                ['coverage1.xml', 'coverage2.xml'],
                                'mult_inputs_html_report.html')

    def test_mult_inputs_console(self):
        self._check_console_report('git_diff_mult.txt',
                                   ['coverage1.xml', 'coverage2.xml'],
                                   'mult_inputs_console_report.txt')

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
        self._check_html_report('git_diff_violations.txt',
                                [],
                                'pep8_violations_report.html',
                                'pep8')

    def test_added_file_pylint_html(self):
        self._check_html_report('git_diff_violations.txt',
                                [],
                                'pylint_violations_report.html',
                                'pylint')

    def test_added_file_pep8_console(self):
        self._check_console_report('git_diff_violations.txt',
                                   [],
                                   'pep8_violations_report.txt',
                                   'pep8')

    def test_added_file_pylint_console(self):
        self._check_console_report('git_diff_violations.txt',
                                   [],
                                   'pylint_violations_report.txt',
                                   'pylint')
