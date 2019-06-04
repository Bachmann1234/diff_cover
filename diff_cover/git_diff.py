"""
Wrapper for `git diff` command.
"""
from __future__ import unicode_literals

from diff_cover.command_runner import execute


class GitDiffError(Exception):
    """
    `git diff` command produced an error.
    """
    pass


class GitDiffTool(object):
    """
    Thin wrapper for a subset of the `git diff` command.
    """

    def __init__(self, range_notation):
        """
        :param str range_notation:
            which range notation to use when producing the diff for committed
            files against another branch.

            Traditionally in git-cover the symmetric difference (three-dot, "A...M") notation has been used: it
            includes commits reachable from A and M from their merge-base, but not both, taking history in account.
            This includes cherry-picks between A and M, which are harmless and do not produce changes, but might give
            inaccurate coverage false-negatives.

            Two-dot range notation ("A..M") compares the tips of both trees and produces a diff. This more accurately
            describes the actual patch that will be applied by merging A into M, even if commits have been
            cherry-picked between branches. This will produce a more accurate diff for coverage comparison when
            complex merges and cherry-picks are involved.
        """
        self._range_notation = range_notation

    def diff_committed(self, compare_branch='origin/master'):
        """
        Returns the output of `git diff` for committed
        changes not yet in origin/master.

        Raises a `GitDiffError` if `git diff` outputs anything
        to stderr.
        """
        return execute([
            'git',
            '-c', 'diff.mnemonicprefix=no',
            '-c', 'diff.noprefix=no',
            'diff', '{branch}{notation}HEAD'.format(branch=compare_branch, notation=self._range_notation),
            '--no-color',
            '--no-ext-diff'
        ])[0]

    def diff_unstaged(self):
        """
        Returns the output of `git diff` with no arguments, which
        is the diff for unstaged changes.

        Raises a `GitDiffError` if `git diff` outputs anything
        to stderr.
        """
        return execute([
            'git',
            '-c', 'diff.mnemonicprefix=no',
            '-c', 'diff.noprefix=no',
            'diff',
            '--no-color',
            '--no-ext-diff'
        ])[0]

    def diff_staged(self):
        """
        Returns the output of `git diff --cached`, which
        is the diff for staged changes.

        Raises a `GitDiffError` if `git diff` outputs anything
        to stderr.
        """
        return execute([
            'git',
            '-c', 'diff.mnemonicprefix=no',
            '-c', 'diff.noprefix=no',
            'diff',
            '--cached',
            '--no-color',
            '--no-ext-diff'
        ])[0]
