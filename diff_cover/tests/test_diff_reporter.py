import unittest
import mock
from textwrap import dedent
from diff_cover.diff_reporter import GitDiffReporter
from diff_cover.git_diff import GitDiffTool, GitDiffError
from helpers import line_numbers, git_diff_output


class GitDiffReporterTest(unittest.TestCase):

    MASTER_DIFF = git_diff_output(
            {'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)},
            line_buffer=False
            )
    
    STAGED_DIFF = git_diff_output(
            {'subdir/file2.py': line_numbers(3, 10),
             'one_line.txt': [1]},
            line_buffer=False)

    UNSTAGED_DIFF = git_diff_output(
            dict(),
            deleted_files=['README.md'],
            line_buffer=False)

    def setUp(self):

        # Create a mock git diff wrapper
        self._git_diff = mock.MagicMock(GitDiffTool)

        # Create the diff reporter
        self.diff = GitDiffReporter(git_diff=self._git_diff)

    def test_name(self):

        # Expect that diff report is named after its compare branch
        self.assertEqual(self.diff.name(),
                         'origin/master...HEAD, staged, and unstaged changes')

    def test_git_source_paths(self):

        # Configure the git diff output
        self._set_git_diff_output(self.MASTER_DIFF, self.STAGED_DIFF,
                                  self.UNSTAGED_DIFF)

        # Get the source paths in the diff
        source_paths = self.diff.src_paths_changed()

        # Validate the source paths
        # They should be in alphabetical order
        self.assertEqual(len(source_paths), 4)
        self.assertEqual('one_line.txt', source_paths[0])
        self.assertEqual('README.md', source_paths[1])
        self.assertEqual('subdir/file1.py', source_paths[2])
        self.assertEqual('subdir/file2.py', source_paths[3])

    def test_duplicate_source_paths(self):

        # Duplicate the output for committed, staged, and unstaged changes
        self._set_git_diff_output(self.MASTER_DIFF, self.MASTER_DIFF,
                                  self.MASTER_DIFF)

        # Get the source paths in the diff
        source_paths = self.diff.src_paths_changed()

        # Should see only one copy of source files in MASTER_DIFF
        self.assertEqual(len(source_paths), 1)
        self.assertEqual('subdir/file1.py', source_paths[0])

    def test_git_lines_changed(self):

        # Configure the git diff output
        self._set_git_diff_output(self.MASTER_DIFF, self.STAGED_DIFF,
                                  self.UNSTAGED_DIFF)

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('subdir/file1.py')

        # Validate the lines changed
        self.assertEqual(lines_changed, line_numbers(3, 10) + 
                                        line_numbers(34, 47))

    def test_git_deleted_lines(self):

        # Configure the git diff output
        self._set_git_diff_output(self.MASTER_DIFF, self.STAGED_DIFF,
                                  self.UNSTAGED_DIFF)

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('README.md')

        # Validate no lines changed
        self.assertEqual(len(lines_changed), 0)

    def test_git_repeat_lines(self):

        # Same committed, staged, and unstaged lines
        self._set_git_diff_output(self.MASTER_DIFF, self.MASTER_DIFF,
                                  self.MASTER_DIFF)

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('subdir/file1.py')

        # Validate the lines changed
        self.assertEqual(lines_changed, line_numbers(3, 10) +
                                        line_numbers(34, 47))

    def test_git_overlapping_lines(self):

        # Overlap, extending the end of the hunk (lines 3 to 10)
        overlap_1 = dedent("""
        diff --git a/subdir/file1.py b/subdir/file1.py
        @@ -3,6 +5,9 @@ Text
        """).strip()

        # Overlap, extending the beginning of the hunk (lines 34 to 47)
        overlap_2 = dedent("""
        diff --git a/subdir/file1.py b/subdir/file1.py
        @@ -33,10 +32,5 @@ Text
        """).strip()

        # Lines in staged / unstaged overlap with lines in master
        self._set_git_diff_output(self.MASTER_DIFF, overlap_1, overlap_2)

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('subdir/file1.py')

        # Validate the lines changed
        self.assertEqual(lines_changed, line_numbers(3, 14) +
                                        line_numbers(32, 47))

    def test_git_line_within_hunk(self):

        # Surround hunk in master (lines 3 to 10)
        surround = dedent("""
        diff --git a/subdir/file1.py b/subdir/file1.py
        @@ -3,6 +2,9 @@ Text
        """).strip()

        # Within hunk in master (lines 34 to 47)
        within = dedent("""
        diff --git a/subdir/file1.py b/subdir/file1.py
        @@ -33,10 +35,11 @@ Text
        """).strip()

        # Lines in staged / unstaged overlap with hunks in master
        self._set_git_diff_output(self.MASTER_DIFF, surround, within)

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('subdir/file1.py')

        # Validate the lines changed
        self.assertEqual(lines_changed, line_numbers(2, 11) +
                                        line_numbers(34, 47))

    def test_git_no_such_file(self):

        # Configure the git diff output
        self._set_git_diff_output(self.MASTER_DIFF, self.STAGED_DIFF,
                                  self.UNSTAGED_DIFF)

        lines_changed = self.diff.lines_changed('no_such_file.txt')
        self.assertEqual(len(lines_changed), 0)

    def test_no_diff(self):

        # Configure the git diff output
        self._set_git_diff_output('', '', '')

        # Expect no files changed
        source_paths = self.diff.src_paths_changed()
        self.assertEqual(source_paths, [])

    def test_git_diff_error(self):

        invalid_hunk_str = dedent("""
                           diff --git a/subdir/file1.py b/subdir/file1.py
                           @@ invalid @@ Text
                           """).strip()

        no_src_line_str = "@@ -33,10 +34,13 @@ Text"
        non_numeric_lines = dedent("""
                            diff --git a/subdir/file1.py b/subdir/file1.py
                            @@ -1,2 +a,b @@
                            """).strip()
        missing_line_num = dedent("""
                            diff --git a/subdir/file1.py b/subdir/file1.py
                            @@ -1,2 +  @@
                            """).strip()

        # List of (stdout, stderr) git diff pairs that should cause
        # a GitDiffError to be raised.
        err_outputs = [invalid_hunk_str, no_src_line_str,
                       non_numeric_lines, missing_line_num]

        for diff_str in err_outputs:

            # Configure the git diff output
            self._set_git_diff_output(diff_str, '', '')

            fail_msg = "Failed for '{0}'".format(diff_str)

            # Expect that both methods that access git diff raise an error
            with self.assertRaises(GitDiffError, msg=fail_msg):
                self.diff.src_paths_changed()

            with self.assertRaises(GitDiffError, msg=fail_msg):
                self.diff.lines_changed('subdir/file1.py')

    def _set_git_diff_output(self, committed_diff, staged_diff, unstaged_diff):
        """
        Configure the git diff tool to return `committed_diff`,
        `staged_diff`, and `unstaged_diff` as outputs from
        `git diff`
        """
        self._git_diff.diff_committed.return_value = committed_diff
        self._git_diff.diff_staged.return_value = staged_diff
        self._git_diff.diff_unstaged.return_value = unstaged_diff
