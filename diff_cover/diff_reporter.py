"""
Classes for querying which lines have changed based on a diff.
"""

from abc import ABCMeta, abstractmethod
from git_diff import GitDiffTool, GitDiffError
import re


class BaseDiffReporter(object):
    """
    Query information about lines changed in a diff.
    """

    __metaclass__ = ABCMeta

    def __init__(self, name):
        """
        Provide a `name` for the diff report, which will
        be included in the diff coverage report.
        """
        self._name = name

    @abstractmethod
    def src_paths_changed(self):
        """
        Returns a list of source paths changed in this diff.

        Source paths are guaranteed to be unique.
        """
        pass

    @abstractmethod
    def hunks_changed(self, src_path):
        """
        Returns a list of hunks changed in the source file at `src_path`.
        Each hunk is a `(start_line, end_line)` tuple indicating
        the starting and ending line numbers of the hunk
        in the current version of the source file.

        Hunks are guaranteed to be non-overlapping.
        """
        pass

    def name(self):
        """
        Return the name of the diff, which will be included
        in the diff coverage report.
        """
        return self._name


class GitDiffReporter(BaseDiffReporter):
    """
    Query information from a Git diff between branches.
    """

    def __init__(self, git_diff=None):
        """
        Configure the reporter to use `git_diff` as the wrapper
        for the `git diff` tool.  (Should have same interface
        as `git_diff.GitDiffTool`
        """
        super(GitDiffReporter, self).__init__('master...HEAD, staged, and unstaged changes')

        self._git_diff_tool = git_diff

        # Cache diff information as a dictionary
        # with file path keys and hunk list values
        self._diff_dict = None

    def src_paths_changed(self):

        # Get the diff dictionary
        diff_dict = self._git_diff()

        # Return the changed file paths (dict keys)
        # in alphabetical order
        return sorted(diff_dict.keys(), key=str.lower)

    def hunks_changed(self, src_path):

        # Get the diff dictionary
        diff_dict = self._git_diff()

        # Return the list `(start_line, end_line)` hunks
        # for the file at `src_path`
        # If no such file, return an empty list.
        return diff_dict.get(src_path, [])

    def _git_diff(self):
        """
        Run `git diff` and returns a dict in which the keys
        are changed file paths and the values are lists of
        `(start_line, end_line)` tuples.

        Returns a cached result if called multiple times.

        Raises a GitDiffError if `git diff` has an error.
        """

        # If we do not have a cached result, execute `git diff`
        if self._diff_dict is None:

            # Get the output of `git diff`
            diff_str = self._git_diff_str()

            # Parse the output of the diff string
            self._diff_dict = self._parse_diff_str(diff_str)

            # Resolve overlapping hunks
            for (src_path, hunk_list) in self._diff_dict.items():
                self._diff_dict[src_path] = self._resolve_overlaps(hunk_list)

        # Return the diff cache
        return self._diff_dict

    def _git_diff_str(self):
        """
        Execute `git diff` and return the output string,
        raising a GitDiffError if `git diff` reports an error.
        """

        # Execute `git diff` for each changeset we need
        output = [self._git_diff_tool.diff_committed(),
                  self._git_diff_tool.diff_unstaged(),
                  self._git_diff_tool.diff_staged()]


        # Return the concatenated output string
        return "\n".join(output)

    # Regular expressions used to parse the diff output
    SRC_FILE_RE = re.compile('^diff --git a/.* b/([^ \n]*)')
    HUNK_LINE_RE = re.compile('^@@ -.* \+([0-9,]*) @@')

    def _parse_diff_str(self, diff_str):
        """
        Parse the output of `git diff` into a dictionary with
        keys that are the source file paths, and values
        that are lists of `(start_line, end_line)` hunks
        changed.

        If the output could not be parsed, raises a GitDiffError.
        """

        # Create a dict to hold results
        diff_dict = dict()

        # Keep track of the current source file
        src_path = None

        # Split the diff string into lines
        for line in diff_str.split('\n'):

            # If the line starts with "diff --git", try to parse the
            # source path.
            if line.startswith('diff --git'):
                src_path = self._parse_source_line(line, diff_dict)

            # If the line starts with "@@", try to parse the hunk
            # start and end lines
            elif line.startswith('@@'):
                self._parse_hunk_line(line, src_path, diff_dict)
            # Ignore all other lines

        return diff_dict

    def _parse_source_line(self, line, diff_dict):
        """
        Parse `line` for the source file path.
        Update `diff_dict` with key for the path and an empty list value,
        and return the source path.
        """
        groups = self.SRC_FILE_RE.findall(line)

        if len(groups) == 1:

            # Store the name of the source path
            src_path = groups[0]

            # If there is not a list for this source path
            # already, create one.
            if src_path not in diff_dict:
                diff_dict[src_path] = []

        # Something invalid in the format
        # Rather than risk misinterpreting the diff, raise an exception
        else:
            raise GitDiffError("Could not parse '{0}'".format(line))

        return src_path

    def _parse_hunk_line(self, line, src_path, diff_dict):
        """
        Parse a line containing a "hunk" of code (start/end line numbers).
        Update `diff_dict[src_path]` by appending `(start_line, end_line)`
        tuple to the value (a list)
        """
        groups = self.HUNK_LINE_RE.findall(line)

        if len(groups) == 1:

            hunk_str = groups[0]

            # Split is guaranteed to return at least one component,
            # so we handle only the cases where len(components) >= 1 below.
            components = hunk_str.split(',')

            # Calculate the end line (counting start_line as the first)
            # Handle the case in which num_lines is not specified
            # (because there is only one line in the file)
            try:
                if len(components) == 1:
                    start_line = int(components[0])
                    end_line = start_line

                elif len(components) > 1:
                    start_line = int(components[0])
                    num_lines = int(components[1])
                    end_line = start_line + num_lines

            except ValueError:
                raise GitDiffError("Could not parse hunk '{0}'".format(line))

            # Add the hunk to the current source file
            if src_path is not None:
                hunk = (start_line, end_line)

                # Handle the special case in which a file is deleted
                if hunk == (0, 0):
                    pass
                else:
                    diff_dict[src_path].append(hunk)

            # Got a hunk before a source file: input string is invalid
            else:
                msg = "Hunk has no source file: '{0}'".format(line)
                raise GitDiffError(msg)

        else:
            raise GitDiffError("Could not parse '{0}'".format(line))

    def _resolve_overlaps(self, hunk_list):
        """
        Given a list of `(start_line, end_line)` tuples representing
        hunks in a file, return a list in which all overlapping hunks
        have been combined.
        """

        if len(hunk_list) == 0:
            return []

        # First, sort the hunks into ascending order by start line
        sorted_hunks = sorted(hunk_list, key=lambda hunk: hunk[0])

        # Iterate through the hunks, combining overlaps
        last_hunk = sorted_hunks[0]
        results = [last_hunk]
        for hunk in sorted_hunks[1:]:
            (last_start, last_end) = last_hunk
            (start, end) = hunk

            # If the start of the current hunk is less than the
            # end of the last hunk, combine them
            # Choose the max of (end, last_end)
            # to handle the case where the new hunk is entirely
            # within the last hunk.
            if start < last_end:
                results[-1] = (last_start, max(end, last_end))

            # Otherwise, add a new hunk
            else:
                results.append(hunk)

            # Store the last hunk
            last_hunk = hunk

        return results
