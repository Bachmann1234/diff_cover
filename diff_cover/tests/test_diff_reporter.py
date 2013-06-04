import unittest
import mock
from textwrap import dedent
from diff_cover.diff_reporter import GitDiffReporter
from diff_cover.git_diff import GitDiffTool, GitDiffError


class GitDiffReporterTest(unittest.TestCase):

    MASTER_DIFF = dedent("""
    diff --git a/subdir/file1.py b/subdir/file1.py
    index 629e8ad..91b8c0a 100644
    --- a/subdir/file1.py
    +++ b/subdir/file1.py
    @@ -3,6 +3,7 @@ Text
    More text
    Even more text

    @@ -33,10 +34,13 @@ Text
     More text
    +Another change
    """).strip()

    STAGED_DIFF = dedent("""
    diff --git a/subdir/file2.py b/subdir/file2.py
    index 629e8ad..91b8c0a 100644
    --- a/subdir/file2.py
    +++ b/subdir/file2.py
    @@ -3,6 +3,7 @@ Text
     More text
    -Even more text

    diff --git a/one_line.txt b/one_line.txt
    @@ -1,18 +1 @@
    Test of one line left
    """).strip()

    UNSTAGED_DIFF = dedent("""
    diff --git a/README.md b/README.md
    deleted file mode 100644
    index 1be20b5..0000000
    --- a/README.md
    +++ /dev/null
    @@ -1,18 +0,0 @@
    -diff-cover
    -==========
    -
    -Automatically find diff lines that need test coverage.
    -
    """).strip()

    def setUp(self):

        # Create a mock git diff wrapper
        self._git_diff = mock.MagicMock(GitDiffTool)

        # Create the diff reporter
        self.diff = GitDiffReporter(git_diff=self._git_diff)

    def test_name(self):

        # Expect that diff report is named after its compare branch
        self.assertEqual(self.diff.name(), 
                         'master...HEAD, staged, and unstaged changes')

    def test_git_source_paths(self):

        # Configure the git diff output
        self._set_git_diff_output(self.MASTER_DIFF, self.STAGED_DIFF,
                                  self.UNSTAGED_DIFF)

        # Get the source paths in the diff
        source_paths = self.diff.src_paths_changed()

        # Validate the source paths
        self.assertEqual(len(source_paths), 4)
        self.assertIn('subdir/file1.py', source_paths)
        self.assertIn('subdir/file2.py', source_paths)
        self.assertIn('one_line.txt', source_paths)
        self.assertIn('README.md', source_paths)

    def test_git_hunks_changed(self):

        # Configure the git diff output
        self._set_git_diff_output(self.MASTER_DIFF, self.STAGED_DIFF,
                                  self.UNSTAGED_DIFF)

        # Get the hunks changed in the diff
        hunks_changed = self.diff.hunks_changed('subdir/file1.py')

        # Validate the hunks changed
        self.assertEqual(len(hunks_changed), 2)
        self.assertEqual(hunks_changed[0], (3, 10))
        self.assertEqual(hunks_changed[1], (34, 47))

    def test_git_deleted_hunk(self):

        # Configure the git diff output
        self._set_git_diff_output(self.MASTER_DIFF, self.STAGED_DIFF,
                                  self.UNSTAGED_DIFF)

        # Get the hunks changed in the diff
        hunks_changed = self.diff.hunks_changed('README.md')

        # Validate no hunks changed
        self.assertEqual(len(hunks_changed), 0)

    def test_git_no_such_file(self):

        # Configure the git diff output
        self._set_git_diff_output(self.MASTER_DIFF, self.STAGED_DIFF,
                                  self.UNSTAGED_DIFF)

        hunks_changed = self.diff.hunks_changed('no_such_file.txt')
        self.assertEqual(hunks_changed, [])

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
                self.diff.hunks_changed('subdir/file1.py')

    def _set_git_diff_output(self, committed_diff, staged_diff, unstaged_diff):
        """
        Configure the git diff tool to return `committed_diff`,
        `staged_diff`, and `unstaged_diff` as outputs from
        `git diff`
        """
        self._git_diff.diff_committed.return_value = committed_diff
        self._git_diff.diff_staged.return_value = staged_diff
        self._git_diff.diff_unstaged.return_value = unstaged_diff
