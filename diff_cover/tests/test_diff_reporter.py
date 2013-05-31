import unittest
import mock
from textwrap import dedent
from diff_cover.diff_reporter import GitDiffReporter, GitDiffError

class GitDiffReporterTest(unittest.TestCase):

    GIT_DIFF_OUTPUT = dedent("""
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

        # Create a mock subprocess module
        self.subprocess = mock.Mock()
        self.process = mock.Mock()
        self.subprocess.Popen = mock.Mock(return_value=self.process)
        self.process.communicate = mock.Mock()

        # Create the diff reporter
        compare_branch = 'master'
        self.diff = GitDiffReporter(compare_branch, 
                                    subprocess_mod=self.subprocess)


    def test_popen_src_paths(self):

        # Configure the git diff output
        self._set_git_diff_output(self.GIT_DIFF_OUTPUT, '')

        # Call the interface method
        self.diff.src_paths_changed()

        # Expect that subprocess.Popen() was configured correctly
        self.subprocess.Popen.assert_called_with(['git', 'diff', 'master'],
                                                 stdout=self.subprocess.PIPE,
                                                 stderr=self.subprocess.PIPE)

    def test_popen_hunks_changed(self):

        # Configure the git diff output
        self._set_git_diff_output(self.GIT_DIFF_OUTPUT, '')

        # Call the interface method
        self.diff.hunks_changed('subdir/file1.py')

        # Expect that subprocess.Popen() was configured correctly
        self.subprocess.Popen.assert_called_with(['git', 'diff', 'master'],
                                                 stdout=self.subprocess.PIPE,
                                                 stderr=self.subprocess.PIPE)


    def test_git_source_paths(self):

        # Configure the git diff output
        self._set_git_diff_output(self.GIT_DIFF_OUTPUT, '')

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
        self._set_git_diff_output(self.GIT_DIFF_OUTPUT, '')

        # Get the hunks changed in the diff
        hunks_changed = self.diff.hunks_changed('subdir/file1.py')

        # Validate the hunks changed
        self.assertEqual(len(hunks_changed), 2)
        self.assertEqual(hunks_changed[0], (3, 10))
        self.assertEqual(hunks_changed[1], (34, 47))

    def test_git_deleted_hunk(self):

        # Configure the git diff output
        self._set_git_diff_output(self.GIT_DIFF_OUTPUT, '')

        # Get the hunks changed in the diff
        hunks_changed = self.diff.hunks_changed('README.md')

        # Validate no hunks changed
        self.assertEqual(len(hunks_changed), 0)

    def test_git_no_such_file(self):

        # Configure the git diff output
        self._set_git_diff_output(self.GIT_DIFF_OUTPUT, '')

        hunks_changed = self.diff.hunks_changed('no_such_file.txt')
        self.assertEqual(hunks_changed, [])

    def test_no_diff(self):

        # Configure the process to return with an empty string
        self._set_git_diff_output('', '')

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
        err_outputs = [ ('', 'fatal error occurred'),
                        (invalid_hunk_str, ''), 
                        (no_src_line_str, ''),
                        (non_numeric_lines, '')]

        for (stdout_str, stderr_str) in err_outputs:

            # Configure the process to return the output
            self._set_git_diff_output(stdout_str, stderr_str)

            fail_msg = "Failed for stdout='{0}' and stderr='{1}'".format(
                    stdout_str, stderr_str)

            # Expect that both methods that access git diff raise an error
            with self.assertRaises(GitDiffError, msg=fail_msg):
                self.diff.src_paths_changed()

            with self.assertRaises(GitDiffError, msg=fail_msg):
                self.diff.hunks_changed('subdir/file1.py')

    def _set_git_diff_output(self, stdout_str, stderr_str):
        """ 
        Configure the git diff process to print `stdout_str` to stdout
        and `stderr_str` to stderr.
        """
        self.process.communicate.return_value = (stdout_str, stderr_str)
