from __future__ import unicode_literals
import mock
from diff_cover.git_diff import GitDiffTool, GitDiffError
from diff_cover.tests.helpers import unittest


class TestGitDiffTool(unittest.TestCase):

    def setUp(self):

        # Create mock subprocess to simulate `git diff`
        self.subprocess = mock.Mock()
        self.process = mock.Mock()
        self.subprocess.Popen = mock.Mock(return_value=self.process)
        self.process.communicate = mock.Mock()

        # Create the git diff tool
        self.tool = GitDiffTool(subprocess_mod=self.subprocess)

    def test_diff_committed(self):

        self._set_git_diff_output('test output', '')
        output = self.tool.diff_committed()

        # Expect that we get the correct output
        self.assertEqual(output, 'test output')

        # Expect that the correct command was executed
        expected = ['git', 'diff', 'origin/master...HEAD', '--no-ext-diff']
        self.subprocess.Popen.assert_called_with(
            expected, stdout=self.subprocess.PIPE, stderr=self.subprocess.PIPE
        )

    def test_diff_unstaged(self):
        self._set_git_diff_output('test output', '')
        output = self.tool.diff_unstaged()

        # Expect that we get the correct output
        self.assertEqual(output, 'test output')

        # Expect that the correct command was executed
        expected = ['git', 'diff', '--no-ext-diff']
        self.subprocess.Popen.assert_called_with(
            expected, stdout=self.subprocess.PIPE, stderr=self.subprocess.PIPE
        )

    def test_diff_staged(self):
        self._set_git_diff_output('test output', '')
        output = self.tool.diff_staged()

        # Expect that we get the correct output
        self.assertEqual(output, 'test output')

        # Expect that the correct command was executed
        expected = ['git', 'diff', '--cached', '--no-ext-diff']
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
        expected = ['git', 'diff', 'release...HEAD', '--no-ext-diff']
        self.subprocess.Popen.assert_called_with(
            expected, stdout=self.subprocess.PIPE, stderr=self.subprocess.PIPE
        )

    def test_errors(self):
        self._set_git_diff_output('test output', 'fatal error')

        with self.assertRaises(GitDiffError):
            self.tool.diff_unstaged()

        with self.assertRaises(GitDiffError):
            self.tool.diff_staged()

        with self.assertRaises(GitDiffError):
            self.tool.diff_unstaged()

    def _set_git_diff_output(self, stdout, stderr):
        """
        Configure the `git diff` mock to output `stdout`
        and `stderr` to stdout and stderr, respectively.
        """
        self.process.communicate.return_value = (stdout, stderr)
