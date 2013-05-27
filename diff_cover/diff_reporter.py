"""
Classes for querying which lines have changed based on a diff.
"""

from abc import ABCMeta, abstractmethod

class BaseDiffReporter(object):
    """
    Query information about lines changed in a diff.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def src_paths_changed(self):
        """
        Returns a list of source paths changed in this diff.
        """
        pass

    @abstractmethod
    def hunks_changed(self, src_path):
        """
        Returns a list of hunks changed in the source file at `src_path`.
        Each hunk is a `(start_line, end_line)` tuple indicating
        the starting and ending line numbers of the hunk
        in the current version of the source file.
        """
        pass

class GitDiffReporter(BaseDiffReporter):
    """
    Query information from a Git diff between branches.
    """
    
    def __init__(self, compare_branch):
        """
        Configure the reporter to compare the current repo branch
        with `compare_branch`.
        """
        super(GitDiffReporter, self).__init__()

    def src_paths_changed(self):
        pass

    def hunks_changed(self, src_path):
        pass
