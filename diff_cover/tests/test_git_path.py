from __future__ import unicode_literals
import mock
from diff_cover.git_path import GitPathTool
from diff_cover.tests.helpers import unittest


class TestGitPathTool(unittest.TestCase):

    def setUp(self):
        # Create mock subprocess to simulate `git rev-parse`
        self.process = mock.Mock()
        self.subprocess = mock.patch('diff_cover.git_path.subprocess').start()
        self.subprocess.Popen.return_value = self.process

    def tearDown(self):
        mock.patch.stopall()

    def test_project_root_command(self):
        self._set_git_root('/phony/path')

        GitPathTool('/phony/path')

        # Expect that the correct command was executed
        expected = ['git', 'rev-parse', '--show-toplevel']
        self.subprocess.Popen.assert_called_with(
            expected, stdout=self.subprocess.PIPE, stderr=self.subprocess.PIPE
        )

    def test_relative_path(self):
        self._set_git_root('/home/user/work/diff-cover')
        expected = 'violations_reporter.py'
        cwd = '/home/user/work/diff-cover/diff_cover'

        tool = GitPathTool(cwd)
        path = tool.relative_path('diff_cover/violations_reporter.py')

        # Expect relative path from diff_cover
        self.assertEqual(path, expected)

    def test_absolute_path(self):
        self._set_git_root('/home/user/work/diff-cover')
        expected = '/home/user/work/diff-cover/other_package/file.py'
        cwd = '/home/user/work/diff-cover/diff_cover'

        tool = GitPathTool(cwd)
        path = tool.absolute_path('other_package/file.py')

        # Expect absolute path to file.py
        self.assertEqual(path, expected)

    def _set_git_root(self, git_root):
        """
        Configure the process mock to output `stdout`
        to a given git project root.
        """
        self.process.communicate.return_value = (git_root, '')
