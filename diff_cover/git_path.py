"""
Converter for `git diff` paths
"""
from __future__ import unicode_literals
import os
import six
import subprocess


class GitPathTool(object):
    """
    Converts `git diff` paths to absolute paths or relative paths to cwd.
    """

    def __init__(self, cwd):
        """
        Initialize the absolute path to the git project
        """
        self._cwd = cwd
        self._root = self._git_root()

    def relative_path(self, git_diff_path):
        """
        Returns git_diff_path relative to cwd.
        """
        # Remove git_root from src_path for searching the correct filename
        # If cwd is `/home/user/work/diff-cover/diff_cover`
        # and src_path is `diff_cover/violations_reporter.py`
        # search for `violations_reporter.py`
        root_rel_path = os.path.relpath(self._cwd, self._root)
        if six.PY2:
            git_diff_path = git_diff_path.encode('utf-8')
        return os.path.relpath(git_diff_path, root_rel_path)

    def absolute_path(self, src_path):
        """
        Returns absoloute git_diff_path
        """
        # If cwd is `/home/user/work/diff-cover/diff_cover`
        # and src_path is `other_package/some_file.py`
        # search for `/home/user/work/diff-cover/other_package/some_file.py`
        return os.path.join(self._root, src_path)

    def _git_root(self):
        """
        Returns the output of `git rev-parse --show-toplevel`, which
        is the absolute path for the git project root.
        """
        command = ['git', 'rev-parse', '--show-toplevel']
        process = subprocess.Popen(command,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        return stdout.strip()

