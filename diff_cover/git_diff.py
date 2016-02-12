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

    def diff_committed(self, compare_branch='origin/master'):
        """
        Returns the output of `git diff` for committed
        changes not yet in origin/master.

        Raises a `GitDiffError` if `git diff` outputs anything
        to stderr.
        """
        return execute([
            'git', '-c', 'diff.mnemonicprefix=no', 'diff',
            "{branch}...HEAD".format(branch=compare_branch),
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
        return execute(['git', '-c', 'diff.mnemonicprefix=no', 'diff',
                        '--no-color', '--no-ext-diff'])[0]

    def diff_staged(self):
        """
        Returns the output of `git diff --cached`, which
        is the diff for staged changes.

        Raises a `GitDiffError` if `git diff` outputs anything
        to stderr.
        """
        return execute(['git', '-c', 'diff.mnemonicprefix=no', 'diff',
                        '--cached', '--no-color', '--no-ext-diff'])[0]
