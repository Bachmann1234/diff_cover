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
    This class is a singleton because the same path will be used accross
    the project
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            if len(args) != 1:
                raise TypeError(("First call to GitPathTool() must be done"
                                 " with the `cwd` argument"))
            cls._instance = super(GitPathTool, cls).__new__(cls)
            cls._instance.__init__(*args, **kwargs)
        return cls._instance

    def __init__(self, cwd=None):
        """
        Initialize the absolute path to the git project
        """
        if cwd is None:
            return

        self._cwd = self._decode(cwd)
        self._root = self._decode(self._git_root())

    def relative_path(self, git_diff_path):
        """
        Returns git_diff_path relative to cwd.
        """
        # Remove git_root from src_path for searching the correct filename
        # If cwd is `/home/user/work/diff-cover/diff_cover`
        # and src_path is `diff_cover/violations_reporter.py`
        # search for `violations_reporter.py`
        root_rel_path = os.path.relpath(self._cwd, self._root)
        root_rel_path = self._decode(root_rel_path)
        rel_path = os.path.relpath(git_diff_path, root_rel_path)
        rel_path = self._decode(rel_path)

        return rel_path

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

    @classmethod
    def _decode(cls, string):
        if isinstance(string, six.binary_type):
            return string.decode()
        return string

