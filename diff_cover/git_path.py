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
    _cwd = None
    _root = None

    @classmethod
    def set_cwd(cls, cwd):
        """
        Set the cwd that is used to manipulate paths.
        """
        cls._cwd = cls._decode(cwd)
        cls._root = cls._decode(cls._git_root())

    @classmethod
    def relative_path(cls, git_diff_path):
        """
        Returns git_diff_path relative to cwd.
        """
        # Remove git_root from src_path for searching the correct filename
        # If cwd is `/home/user/work/diff-cover/diff_cover`
        # and src_path is `diff_cover/violations_reporter.py`
        # search for `violations_reporter.py`
        root_rel_path = os.path.relpath(cls._cwd, cls._root)
        root_rel_path = cls._decode(root_rel_path)
        rel_path = os.path.relpath(git_diff_path, root_rel_path)
        rel_path = cls._decode(rel_path)

        return rel_path

    @classmethod
    def absolute_path(cls, src_path):
        """
        Returns absoloute git_diff_path
        """
        # If cwd is `/home/user/work/diff-cover/diff_cover`
        # and src_path is `other_package/some_file.py`
        # search for `/home/user/work/diff-cover/other_package/some_file.py`

        return os.path.join(cls._root, src_path)

    @classmethod
    def _git_root(cls):
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

