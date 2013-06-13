"""
High-level integration tests of diff-cover tool.
"""

import unittest
from mock import patch
import os
import os.path
from subprocess import Popen
from StringIO import StringIO
import tempfile
import shutil
from textwrap import dedent
from diff_cover.tool import main
from diff_cover.diff_reporter import GitDiffError
from helpers import line_numbers, git_diff_output


class DiffCoverIntegrationTest(unittest.TestCase):
    """
    High-level integration test.
    The `git diff` is a mock, but everything else is our code.
    """

    MASTER_DIFF = git_diff_output({'subdir/file1.py':
                                   line_numbers(3, 10) + line_numbers(34, 47)})

    STAGED_DIFF = git_diff_output({'subdir/file2.py': line_numbers(3, 10)})

    UNSTAGED_DIFF = git_diff_output({'README.rst': line_numbers(3, 10)})

    COVERAGE_XML = dedent("""
    <coverage>
        <packages>
            <classes>
                <class filename="subdir/file1.py">
                    <methods />
                    <lines>
                        <line hits="0" number="2" />
                        <line hits="1" number="7" />
                        <line hits="0" number="8" />
                    </lines>
                </class>
                <class filename="subdir/file2.py">
                    <methods />
                    <lines>
                        <line hits="0" number="2" />
                        <line hits="1" number="7" />
                        <line hits="0" number="8" />
                    </lines>
                </class>
            </classes>
        </packages>
    </coverage>
    """)

    EXPECTED_CONSOLE_REPORT = dedent("""
    -------------
    Diff Coverage
    Coverage Report: {coverage_xml}
    Diff: origin/master...HEAD, staged, and unstaged changes
    -------------
    subdir/file2.py (50%): Missing line(s) 8
    subdir/file1.py (50%): Missing line(s) 8
    -------------
    Total:   4 line(s)
    Missing: 2 line(s)
    Coverage: 50%
    -------------
    """).strip() + "\n"

    EXPECTED_HTML_REPORT = dedent("""
    <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
    <html>
    <head>
    <meta http-equiv='Content-Type' content='text/html; charset=utf-8'>
    <title>Diff Coverage</title>
    </head>
    <body>
    <h1>Diff Coverage</h1>
    <p>Coverage Report: {coverage_xml}</p>
    <p>Diff: origin/master...HEAD, staged, and unstaged changes</p>
    <table border="1">
    <tr>
    <th>Source File</th>
    <th>Diff Coverage (%)</th>
    <th>Missing Line(s)</th>
    </tr>
    <tr>
    <td>subdir/file2.py</td>
    <td>50%</td>
    <td>8</td>
    </tr>
    <tr>
    <td>subdir/file1.py</td>
    <td>50%</td>
    <td>8</td>
    </tr>
    </table>
    <ul>
    <li><b>Total</b>: 4 line(s)</li>
    <li><b>Missing</b>: 2 line(s)</li>
    <li><b>Coverage</b>: 50%</li>
    </ul>
    </body>
    </html>
    """).strip()

    # Path to the temporary coverage XML file, so we can clean it up later
    _coverage_xml_path = None

    def setUp(self):
        """
        Create fake coverage XML file
        """
        # Write the XML coverage report to a temp directory
        self._coverage_xml_path = self._write_to_temp(self.COVERAGE_XML)

        # Create mocks
        self._mock_communicate = patch.object(Popen, 'communicate').start()
        self._mock_sys = patch('diff_cover.tool.sys').start()

    def tearDown(self):
        """
        Clean up the XML coverage report we created.
        Undo all patches.
        """
        os.remove(self._coverage_xml_path)
        patch.stopall()

    def test_diff_cover_console(self):

        # Patch the output of `git diff`
        self._set_git_diff_outputs([(self.MASTER_DIFF, ""),
                                    (self.STAGED_DIFF, ""),
                                    (self.UNSTAGED_DIFF, "")])

        # Capture stdout to a string buffer
        string_buffer = StringIO()
        self._capture_stdout(string_buffer)

        # Patch sys.argv
        self._set_sys_args(['diff-cover', self._coverage_xml_path])

        # Run diff-cover
        main()

        # Check the output to stdout
        report = string_buffer.getvalue()
        expected = self.EXPECTED_CONSOLE_REPORT.format(coverage_xml=self._coverage_xml_path)
        self.assertEqual(report, expected)

    def test_diff_cover_html(self):

        # Patch the output of `git diff`
        self._set_git_diff_outputs([(self.MASTER_DIFF, ""),
                                    (self.STAGED_DIFF, ""),
                                    (self.UNSTAGED_DIFF, "")])

        # Create a temporary directory to hold the output HTML report
        # Add a cleanup to ensure the directory gets deleted
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(temp_dir))

        # Patch sys.argv
        report_path = os.path.join(temp_dir, 'diff_coverage.html')
        self._set_sys_args(['diff-cover', self._coverage_xml_path,
                            '--html-report', report_path])

        # Run diff-cover
        main()

        # Load the content of the HTML report
        with open(report_path) as html_report:
            html = html_report.read()
            expected = self.EXPECTED_HTML_REPORT.format(coverage_xml=self._coverage_xml_path)
            self.assertEqual(html, expected)

    def test_git_diff_error(self):

        # Patch sys.argv
        self._set_sys_args(['diff-cover', self._coverage_xml_path])

        # Patch the output of `git diff`
        self._set_git_diff_outputs([(self.MASTER_DIFF, ""),
                                    (self.STAGED_DIFF, "fatal error"),
                                    (self.UNSTAGED_DIFF, "")])

        # Expect an error
        with self.assertRaises(GitDiffError):
            main()

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

    def _set_git_diff_outputs(self, outputs):
        """
        Patch the call to `git diff` to return a series of ouputs.
        `outputs` is a list of `(stdout, stderr)` tuples to
        be returned in sequence for each call to subprocess.
        """
        self._mock_communicate.side_effect = outputs

    def _write_to_temp(self, text):
        """
        Write `text` to a temporary file, then return the path.
        """
        _, path = tempfile.mkstemp()

        with open(path, "w") as file_handle:
            file_handle.write(text)
            file_handle.close()

        return path
