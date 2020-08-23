"""
Wrapper for `git diff` command.
"""

from diff_cover.command_runner import execute


class GitDiffError(Exception):
    """
    `git diff` command produced an error.
    """

    pass


class GitDiffTool:
    """
    Thin wrapper for a subset of the `git diff` command.
    """

    def __init__(self, range_notation, ignore_whitespace):
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

         :param bool ignore_whitespace:
            Perform a diff but ignore any and all whitespace.
        """
        self._range_notation = range_notation
        self._default_git_args = [
            "git",
            "-c",
            "diff.mnemonicprefix=no",
            "-c",
            "diff.noprefix=no",
        ]

        self._default_diff_args = ["diff", "--no-color", "--no-ext-diff", "-U0"]

        if ignore_whitespace:
            self._default_diff_args.append("--ignore-all-space")
            self._default_diff_args.append("--ignore-blank-lines")

    def diff_committed(self, compare_branch="origin/master"):
        """
        Returns the output of `git diff` for committed
        changes not yet in origin/master.

        Raises a `GitDiffError` if `git diff` outputs anything
        to stderr.
        """
        diff_range = "{branch}{notation}HEAD".format(
            branch=compare_branch, notation=self._range_notation
        )
        return execute(self._default_git_args + self._default_diff_args + [diff_range])[
            0
        ]

    def diff_unstaged(self):
        """
        Returns the output of `git diff` with no arguments, which
        is the diff for unstaged changes.

        Raises a `GitDiffError` if `git diff` outputs anything
        to stderr.
        """
        return execute(self._default_git_args + self._default_diff_args)[0]

    def diff_staged(self):
        """
        Returns the output of `git diff --cached`, which
        is the diff for staged changes.

        Raises a `GitDiffError` if `git diff` outputs anything
        to stderr.
        """
        return execute(self._default_git_args + self._default_diff_args + ["--cached"])[
            0
        ]
