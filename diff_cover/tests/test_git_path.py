from __future__ import unicode_literals
import mock
from diff_cover.git_path import GitPathTool
from diff_cover.tests.helpers import unittest


class TestGitPathTool(unittest.TestCase):

    def setUp(self):
        # Create mock subprocess to simulate `git rev-parse`
        self.process = mock.Mock()
        self.subprocess = mock.patch('diff_cover.command_runner.subprocess').start()
        self.subprocess.Popen.return_value = self.process

    def tearDown(self):
        mock.patch.stopall()
        # Reset static class members
        GitPathTool._root = None
        GitPathTool._cwd = None

    def test_project_root_command(self):
        self._set_git_root(b'/phony/path')

        GitPathTool.set_cwd(b'/phony/path')

        # Expect that the correct command was executed
        expected = ['git', 'rev-parse', '--show-toplevel', '--encoding=utf-8']
        self.subprocess.Popen.assert_called_with(
            expected, stdout=self.subprocess.PIPE, stderr=self.subprocess.PIPE
        )

    def test_relative_path(self):
        self._set_git_root(b'/home/user/work/diff-cover')
        expected = 'violations_reporter.py'
        cwd = '/home/user/work/diff-cover/diff_cover'

        GitPathTool.set_cwd(cwd)
        path = GitPathTool.relative_path('diff_cover/violations_reporter.py')

        # Expect relative path from diff_cover
        self.assertEqual(path, expected)

    def test_absolute_path(self):
        self._set_git_root(b'/home/user/work dir/diff-cover\n--encoding=utf-8\n')
        expected = '/home/user/work dir/diff-cover/other_package/file.py'
        cwd = '/home/user/work dir/diff-cover/diff_cover'

        GitPathTool.set_cwd(cwd)
        path = GitPathTool.absolute_path('other_package/file.py')

        # Expect absolute path to file.py
        self.assertEqual(path, expected)

    def test_set_cwd_unicode(self):
        self._set_git_root(b"\xe2\x94\xbb\xe2\x94\x81\xe2\x94\xbb")
        expected = '\u253b\u2501\u253b/other_package/file.py'
        cwd = '\\u253b\\u2501\\u253b/diff_cover\n--encoding=utf-8\n'

        GitPathTool.set_cwd(cwd)
        path = GitPathTool.absolute_path('other_package/file.py')

        # Expect absolute path to file.py
        self.assertEqual(path, expected)

    def test_set_cwd_unicode_byte_passed_in_for_cwd(self):
        self._set_git_root(b"\xe2\x94\xbb\xe2\x94\x81\xe2\x94\xbb\n--encoding=utf-8\n")
        expected = '\u253b\u2501\u253b/other_package/file.py'
        cwd = b'\\u253b\\u2501\\u253b/diff_cover'

        GitPathTool.set_cwd(cwd)
        path = GitPathTool.absolute_path('other_package/file.py')

        # Expect absolute path to file.py
        self.assertEqual(path, expected)

    def _set_git_root(self, git_root):
        """
        Configure the process mock to output `stdout`
        to a given git project root.
        """
        self.process.communicate.return_value = (git_root, b'')
