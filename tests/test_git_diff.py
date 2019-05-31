from __future__ import unicode_literals
import mock

from diff_cover.command_runner import CommandError
from diff_cover.git_diff import GitDiffTool
import unittest


class TestGitDiffTool(unittest.TestCase):

    def setUp(self):

        # Create mock subprocess to simulate `git diff`
        self.process = mock.Mock()
        self.process.returncode = 0
        self.subprocess = mock.patch('diff_cover.command_runner.subprocess').start()
        self.subprocess.Popen.return_value = self.process
        # Create the git diff tool
        self.tool = GitDiffTool()

    def test_diff_committed(self):

        self._set_git_diff_output('test output', '')
        output = self.tool.diff_committed()

        # Expect that we get the correct output
        self.assertEqual(output, 'test output')

        # Expect that the correct command was executed
        expected = ['git', '-c', 'diff.mnemonicprefix=no', '-c',
                    'diff.noprefix=no', 'diff', 'origin/master...HEAD',
                    '--no-color', '--no-ext-diff']
        self.subprocess.Popen.assert_called_with(
            expected, stdout=self.subprocess.PIPE, stderr=self.subprocess.PIPE
        )

    def test_diff_unstaged(self):
        self._set_git_diff_output('test output', '')
        output = self.tool.diff_unstaged()

        # Expect that we get the correct output
        self.assertEqual(output, 'test output')

        # Expect that the correct command was executed
        expected = ['git', '-c', 'diff.mnemonicprefix=no', '-c',
                    'diff.noprefix=no', 'diff', '--no-color', '--no-ext-diff']
        self.subprocess.Popen.assert_called_with(
            expected, stdout=self.subprocess.PIPE, stderr=self.subprocess.PIPE
        )

    def test_diff_staged(self):
        self._set_git_diff_output('test output', '')
        output = self.tool.diff_staged()

        # Expect that we get the correct output
        self.assertEqual(output, 'test output')

        # Expect that the correct command was executed
        expected = ['git', '-c', 'diff.mnemonicprefix=no', '-c',
                    'diff.noprefix=no', 'diff', '--cached', '--no-color',
                    '--no-ext-diff']
        self.subprocess.Popen.assert_called_with(
            expected, stdout=self.subprocess.PIPE, stderr=self.subprocess.PIPE
        )

    def test_diff_committed_compare_branch(self):

        # Override the default compare branch
        self._set_git_diff_output('test output', '')
        output = self.tool.diff_committed(compare_branch='release')

        # Expect that we get the correct output
        self.assertEqual(output, 'test output')

        # Expect that the correct command was executed
        expected = ['git', '-c', 'diff.mnemonicprefix=no', '-c',
                    'diff.noprefix=no', 'diff', 'release...HEAD', '--no-color',
                    '--no-ext-diff']
        self.subprocess.Popen.assert_called_with(
            expected, stdout=self.subprocess.PIPE, stderr=self.subprocess.PIPE
        )

    def test_errors(self):
        self._set_git_diff_output('test output', 'fatal error', 1)

        with self.assertRaises(CommandError):
            self.tool.diff_unstaged()

        with self.assertRaises(CommandError):
            self.tool.diff_staged()

        with self.assertRaises(CommandError):
            self.tool.diff_unstaged()

    def _set_git_diff_output(self, stdout, stderr, returncode=0):
        """
        Configure the `git diff` mock to output `stdout`
        and `stderr` to stdout and stderr, respectively.
        """
        self.process.communicate.return_value = (stdout, stderr)
        self.process.returncode = returncode
